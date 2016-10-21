label flow_control:
    label .choice:
        menu:
            "This is the accompanying narration"
            "This is the first choice":
                jump flow_control._choice_01
            "This is the second choice":
                call ._c02
            "A third choice":
                jump other.this_is_ignored
        return
        
    label ._choice_01:
        "Choice 1"
        $ choice = 1
        return
        
    label ._c02:
        "Choice 2"
        $ choice = 2
        return \"foo\"
        
    label .if_elif_else:
        if choice == 1:
            "You chose the first option."
        elif choice == 2:
            "You chose the second option."
        else:
            "You chose the third option."
        return
        
