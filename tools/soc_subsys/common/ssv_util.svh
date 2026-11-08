// Copyright 2026 VIP Portfolio Contributors
// SPDX-License-Identifier: Apache-2.0
//
// ssv_util.svh -- helpers shared by the subsystem tests.

// Demotes UVM errors whose ID is in `ids` to UVM_INFO and counts them per ID,
// so a negative test can provoke a checker on purpose without failing.
class ssv_expect_catcher extends uvm_report_catcher;
  string       ids[$];
  int unsigned caught[string];

  function new(string name = "ssv_expect_catcher");
    super.new(name);
  endfunction

  function int unsigned count(string id);
    return caught.exists(id) ? caught[id] : 0;
  endfunction

  function action_e catch();
    if (get_severity() == UVM_ERROR)
      foreach (ids[i])
        if (get_id() == ids[i]) begin
          if (caught.exists(ids[i])) caught[ids[i]]++; else caught[ids[i]] = 1;
          set_severity(UVM_INFO);
          set_message({"(expected) ", get_message()});
          break;
        end
    return THROW;
  endfunction
endclass
