label other:
    label .this_is_ignored:
        "Nothing here"
        $ choice = 3
        return
        
    label .comments:
        ## copy comment
    ## unindented copy comment
      #~ Oddly indented copy comment with new comment symbol
        return
        
    label .scene_show_with:
        scene scene_01
        show image_01
        with Dissolve(0.5)
        return
        
    label .nvl:
        play char: = CHARACTER
        "This narration is in ADV mode"
        "char: This dialog line is in ADV mode"
        NVL_test "This narration is in NVL mode"
        NVL_test "char: This dialog line is in NVL mode"
        nvl clear
        NVL_test "This NVL line is on the next page"
        "char: This line will be in ADV mode again"
        return
        
    label .misc:
        "Line indentation doesn't matter"
        "As long as it is consistent, just like python."
            "But this'll throw an error"
    "Likewise"
        return
        
    label .logging:
