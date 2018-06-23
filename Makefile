#!/usr/bin/make

.PHONY: tests

tests:
	nosetests3 -v --with-coverage --cover-package=migclic
