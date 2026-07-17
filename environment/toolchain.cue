package toolchain

// bundle is the authority for the first Linux AMD64 tool bundles.
bundle: {
	schema: "cuestrap.toolchain-lock/v1"
	target: {
		os:   "linux"
		arch: "amd64"
	}
	tools: {
		python: {
			version:  "3.14.3"
			revision: "python-build-standalone/20260203"
			source:   "https://github.com/astral-sh/python-build-standalone/releases/download/20260203/cpython-3.14.3%2B20260203-x86_64-unknown-linux-gnu-install_only_stripped.tar.gz"
			sha256:   "d2a2c12cc62b9de249ed9f7c66c6382c76788b464297aaed165853e18643f9e7"
		}
		go: {
			version:  "1.26.5"
			revision: "c19862e5f8415b4f24b189d065ed739517c548ba"
			source:   "https://go.dev/dl/go1.26.5.linux-amd64.tar.gz"
			sha256:   "5c2c3b16caefa1d968a94c1daca04a7ca301a496d9b086e17ad77bb81393f053"
		}
		cue: {
			version:        "0.18.0"
			revision:       "806821e40fae070318600a264d311517e596353b"
			moduleTarget:   "v0.18.0"
			source:         "https://github.com/cue-lang/cue.git"
		}
		gopls: {
			version:  "0.23.0"
			revision: "014f87ff5c01915bc90f4f11a6bb8aea3e0edbd7"
			source:   "https://github.com/golang/tools.git"
		}
		gopy: {
			version:  "0.4.10+cuestrap.72557f6"
			revision: "72557f647208599c726c14dc9721a6c850d2e6d9"
			source:   "https://github.com/go-python/gopy.git"
		}
	}
}
