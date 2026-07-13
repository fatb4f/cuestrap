package fixture

#LowerName: string & =~"^[a-z]+$"

valid: #LowerName & "cue"
invalid: #LowerName & "CUE"
