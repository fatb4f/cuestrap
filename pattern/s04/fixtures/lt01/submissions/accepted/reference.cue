package submission

candidate: {
	candidateID: "accepted-reference"
	cases: {
		"directional-success": {
			left:  int
			right: 1
		}
		"reverse-direction-rejection": {
			left:  1
			right: int
		}
		"adversarial-structural": {
			left: {
				a:  int
				b?: string
			}
			right: {
				b: "x"
				a: 1
			}
		}
	}
}
