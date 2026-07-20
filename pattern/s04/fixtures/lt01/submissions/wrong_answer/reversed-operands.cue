package submission

candidate: {
	candidateID: "rejected-reversed-operands"
	cases: {
		// This candidate erases operand direction and therefore cannot satisfy
		// the reverse-direction case declared by the package.
		"directional-success": {
			left:  int
			right: 1
		}
		"reverse-direction-rejection": {
			left:  int
			right: 1
		}
		"adversarial-structural": {
			left: {
				a:  int
				b?: string
			}
			right: {
				a: 1
				b: "x"
			}
		}
	}
}
