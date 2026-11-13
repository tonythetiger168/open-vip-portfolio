// SPDX-License-Identifier: Apache-2.0
package platform_apb_pkg;
  import uvm_pkg::*;
  `include "uvm_macros.svh"

  class platform_apb_item extends uvm_sequence_item;
    `uvm_object_utils(platform_apb_item)
    bit [31:0] addr, data, read_data;
    bit write_op, error_response, reset_event;
    bit [3:0] strobes;
    function new(string name="platform_apb_item"); super.new(name); endfunction
  endclass

  class platform_apb_driver extends uvm_driver #(platform_apb_item);
    `uvm_component_utils(platform_apb_driver)
    virtual platform_apb_if vif;
    function new(string name, uvm_component parent); super.new(name,parent); endfunction
    function void build_phase(uvm_phase phase);
      super.build_phase(phase);
      if(!uvm_config_db#(virtual platform_apb_if)::get(this,"","vif",vif)) `uvm_fatal("VIF","missing APB interface")
    endfunction
    task run_phase(uvm_phase phase);
      forever begin
        int cycles;
        seq_item_port.get_next_item(req);
        @(negedge vif.pclk);
        vif.psel=1; vif.penable=0; vif.paddr=req.addr; vif.pwrite=req.write_op;
        vif.pwdata=req.data; vif.pstrb=req.strobes;
        @(negedge vif.pclk); vif.penable=1;
        cycles=0;
        do begin @(posedge vif.pclk); cycles++; end while(!vif.pready && cycles<8);
        if(!vif.pready) `uvm_fatal("TIMEOUT","APB request did not complete")
        @(negedge vif.pclk); vif.psel=0; vif.penable=0;
        seq_item_port.item_done();
      end
    endtask
  endclass

  class platform_apb_monitor extends uvm_monitor;
    `uvm_component_utils(platform_apb_monitor)
    virtual platform_apb_if vif;
    uvm_analysis_port #(platform_apb_item) ap;
    function new(string name, uvm_component parent); super.new(name,parent); ap=new("ap",this); endfunction
    function void build_phase(uvm_phase phase);
      super.build_phase(phase);
      if(!uvm_config_db#(virtual platform_apb_if)::get(this,"","vif",vif)) `uvm_fatal("VIF","missing monitor interface")
    endfunction
    task run_phase(uvm_phase phase);
      bit injected=0;
      forever begin
        platform_apb_item sample;
        @(posedge vif.pclk);
        if(!vif.rst_n || (vif.psel && vif.penable && vif.pready)) begin
          sample=platform_apb_item::type_id::create("sample");
          sample.reset_event=!vif.rst_n;
          sample.addr=vif.paddr; sample.write_op=vif.pwrite; sample.data=vif.pwdata;
          sample.strobes=vif.pstrb; sample.read_data=vif.prdata; sample.error_response=vif.pslverr;
          if(!sample.reset_event && !sample.write_op && !injected && $test$plusargs("CORRUPT_MONITOR_ONCE")) begin
            sample.read_data^=32'h1; injected=1;
          end
          if(!sample.reset_event)
            `uvm_info("WIRE",$sformatf("APB_EVENT addr=%08x wr=%0d data=%08x strb=%x read=%08x err=%0d",
              sample.addr,sample.write_op,sample.data,sample.strobes,sample.read_data,sample.error_response),UVM_NONE)
          ap.write(sample);
        end
      end
    endtask
  endclass

  class platform_apb_scoreboard extends uvm_scoreboard;
    `uvm_component_utils(platform_apb_scoreboard)
    uvm_analysis_imp #(platform_apb_item,platform_apb_scoreboard) imp;
    bit [31:0] memory [0:1][0:255];
    int observed=0, checks=0, mismatches=0;
    function new(string name, uvm_component parent); super.new(name,parent); imp=new("imp",this); endfunction
    function void check_expected(bit okay, string message);
      checks++;
      if(!okay) begin mismatches++; `uvm_error("GOLDEN",message) end
    endfunction
    // Predict only from passive accepted/completed wire events, never driver responses/DUT arrays.
    function void write(platform_apb_item t);
      int bank, word_index;
      bit reject;
      if(t.reset_event) begin
        foreach(memory[b,w]) memory[b][w]=0;
      end else begin
        observed++;
        bank=(t.addr>=32'h10001000 && t.addr<32'h10002000)?1:0;
        word_index=int'((t.addr%32'd1024)/32'd4);
        reject=t.addr<32'h10000000 || t.addr>=32'h10002000 || t.addr%4!=0 ||
               (t.addr%4096)>=2048 || (t.write_op && t.strobes!=4'hf);
        check_expected(t.error_response==reject,"response violates independent address/adapter policy");
        if(!reject) begin
          if(t.write_op) memory[bank][word_index]=t.data;
          else check_expected(t.read_data==memory[bank][word_index],"passive memory scoreboard mismatch");
        end
      end
    endfunction
  endclass

  class platform_apb_sequence extends uvm_sequence #(platform_apb_item);
    `uvm_object_utils(platform_apb_sequence)
    int unsigned seed=1, rng;
    function new(string name="platform_apb_sequence"); super.new(name); endfunction
    function bit [31:0] random_word();
      rng^=rng<<13; rng^=rng>>17; rng^=rng<<5; return rng;
    endfunction
    task send_one(bit [31:0] a, bit wr, bit [31:0] d, bit [3:0] s=4'hf);
      platform_apb_item t=platform_apb_item::type_id::create("request");
      start_item(t); t.addr=a; t.write_op=wr; t.data=d; t.strobes=s; finish_item(t);
    endtask
    task body();
      rng=(seed==0)?1:seed;
      send_one(32'h10000000,1,32'h12345678);
      send_one(32'h10000400,0,0);
      send_one(32'h10000000,1,32'hffffffff,4'h3);
      send_one(32'h10000000,0,0);
      send_one(32'h10001000,0,0);
      send_one(32'h20000000,0,0);
      send_one(32'h10000001,0,0);
      send_one(32'h10000800,1,32'hbad);
      // Bounded procedural generation inside a real UVM sequence; no solver claim.
      for(int n=0;n<200;n++) begin
        bit [31:0] r=random_word(), d=random_word(), a;
        bit wr=r[0]; bit [3:0] s=4'hf;
        a=32'h10000000+((r>>1)%2)*4096+((r>>2)%256)*4;
        case((r>>10)%6)
          0:a+=1024;
          1:a=32'h20000000;
          2:a+=1;
          3:begin wr=1;s=4'h5;end
          4:a+=2048;
          default:;
        endcase
        send_one(a,wr,d,s);
      end
    endtask
  endclass

  class platform_apb_env extends uvm_env;
    `uvm_component_utils(platform_apb_env)
    platform_apb_driver driver;
    platform_apb_monitor monitor;
    platform_apb_scoreboard sb;
    uvm_sequencer #(platform_apb_item) sequencer;
    function new(string name, uvm_component parent); super.new(name,parent); endfunction
    function void build_phase(uvm_phase phase);
      super.build_phase(phase);
      driver=platform_apb_driver::type_id::create("driver",this);
      monitor=platform_apb_monitor::type_id::create("monitor",this);
      sb=platform_apb_scoreboard::type_id::create("sb",this);
      sequencer=uvm_sequencer#(platform_apb_item)::type_id::create("sequencer",this);
    endfunction
    function void connect_phase(uvm_phase phase);
      driver.seq_item_port.connect(sequencer.seq_item_export);
      monitor.ap.connect(sb.imp);
    endfunction
  endclass

  class platform_apb_test extends uvm_test;
    `uvm_component_utils(platform_apb_test)
    platform_apb_env env;
    virtual platform_apb_if vif;
    function new(string name, uvm_component parent); super.new(name,parent); endfunction
    function void build_phase(uvm_phase phase);
      super.build_phase(phase);
      env=platform_apb_env::type_id::create("env",this);
      if(!uvm_config_db#(virtual platform_apb_if)::get(this,"","vif",vif)) `uvm_fatal("VIF","missing test interface")
    endfunction
    task run_phase(uvm_phase phase);
      platform_apb_sequence seq=platform_apb_sequence::type_id::create("seq");
      phase.raise_objection(this);
      if($value$plusargs("SEED=%d",seq.seed)) begin end
      wait(vif.rst_n); repeat(2) @(posedge vif.pclk);
      seq.start(env.sequencer);
      repeat(2) @(negedge vif.pclk);
      if(env.sb.observed!=208 || env.sb.checks<208 || env.sb.mismatches!=0)
        `uvm_fatal("AUDIT","missing traffic or passive scoreboard mismatch")
      `uvm_info("RESULT",$sformatf("UVM_PLATFORM_PASS transactions=%0d checks=%0d seed=%0d",env.sb.observed,env.sb.checks,seq.seed),UVM_NONE)
      phase.drop_objection(this);
    endtask
  endclass
endpackage
