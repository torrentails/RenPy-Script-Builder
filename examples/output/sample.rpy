## This comment will though.

label Act_1:
label .scene_01:
    scene tiny_office
    with Fade(1.25)
    "The rain fell heavy on the window as I worked."
    ADAM "I think I need a break."
    "I leaned back in my chair, the monitor glowing softly in font of me."
    "Suddenly I heard a knock at the door to my tiny office."
    ADAM "Come in. The door's unlocked."
    "I turned to face the wooden door as it opened, revealing a familiar face."
    show beth normal at center
    BETH "Hi Adam, how's the script going?"
    ADAM "It's going well, I've made some great progress!"
    ADAM "I'm just taking a bit of break at the moment."
    show beth cheeky at center
    "Beth smiled cheekily. Something was up."
    BETH "Well if you're not busy, perhaps you'd like to meet someone?"
    BETH "You'll like him, I'm sure!"
    ADAM "*sigh* Sure, I don't see why not."
    "I got up and grabbed my jacket and headed out the door with the waiting Beth."

label .scene_02:
    scene office_reception
    with time_skip_transition
    show charles normal at center
    "Standing before me is man in a sharp suit."
    "He almost looks out of place amongst the small, casually dressed team we have."
    show charles handshake at center
    "Upon seeing me, he extends a hand which I take."
    "His grasp is firm as he give my had a shake."
    show charles normal at center
    CHARLES "The name's Charles!"
    CHARLES "I work for Big Name Publishings and we're very interested in the work you and your team have done making visual novels."

    menu:
        CHARLES "We'd like to offer you a lucrative publishing deal for your upcoming games."
        "Accept the offer":
            jump .accept
        "Reject him":
            jump .reject

label .accept:
    "An opportunity like this only comes around once in a life time!"
    ADAM "I'm honoured, of course we'd all be happy to!"
    show charles happy at center
    CHARLES "Fantastic!"
    CHARLES "We'll get the paper work sorted out later."
    show beth smile at right
    BETH "See, I told you you'd like him!"
    scene success
    with time_skip_transition
    "We accepted their deal and became a big name in the industry."
    "We decided to all take a big holiday in Japan to celebrate."
    "THE END"
    return

label .reject:
    "This deal would just mean loss of our creative freedom that we've become known for."
    ADAM "Thank you Charles for the offer..."
    ADAM "But we pride ourselves on our independence and creative freedom."
    ADAM "So I'm going to have to turn you down, sorry."
    show charles mopey at center
    CHARLES "I completely understand, thank you for your time."
    show beth sad at right
    BETH "Aw, I really though this would work."
    scene great_games
    with time_skip_transition
    "Despite not having a lot of budget for our small studio, by sticking to our values we produced many fine games!"
    "THE END"
    return
