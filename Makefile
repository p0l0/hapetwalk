all:
	@echo
	@echo "Available targets"
	@echo ""
	@echo "pre-commit      -- run pre-commit tests"
	@echo ""
	@echo "pylint          -- run pylint tests"
	@echo ""
	@echo "lint            -- run all lint tests"

pre-commit:
	@pre-commit run --all-files

pylint:
	@pylint --jobs=0 custom_components/petwalk

lint: pre-commit pylint

