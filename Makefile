.PHONY: docs

docs:
	$(MAKE) -C docs html

format:
	@isort src
	@black src
