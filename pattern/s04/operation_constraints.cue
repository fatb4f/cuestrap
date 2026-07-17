package s04

// Validation is unary. The base operation shape keeps right optional for the
// binary operation kinds; this refinement makes its presence bottom for
// validate rather than merely leaving it unused.
#PrimitiveOperation: {
	if kind == "validate" {
		right?: _|_
	}
}
