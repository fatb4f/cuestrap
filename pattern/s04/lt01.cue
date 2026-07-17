package s04

#LT01General: {
	service: {
		port: int
	}
}

#LT01Specific: {
	service: {
		port: 8080
	}
}

// These two structural subjects unify, but the left operand does not subsume
// the right because each requires a field absent from the other.
#LT01AdversarialLeft: {
	service: {
		port: int
	}
	mode: "safe"
}

#LT01AdversarialRight: {
	service: {
		port: 8080
	}
	region: "ca"
}
