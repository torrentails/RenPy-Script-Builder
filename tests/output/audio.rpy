label audio:
    label .play:
        play my_channel \"my_sound.ogg\"
        play music \"music.ogg\" fadeout 1.0
        play sound [\"sound.ogg\", \"sound_1.ogg\"]
        play voice \"voice.ogg\"
        play audio \"audio.ogg\"
        
    label .voice:
        voice \"voice.ogg\"
        
    label .queue:
        queue music \"music_2.ogg\"
        
    label .stop:
        stop music
        
