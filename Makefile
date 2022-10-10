PROJECT := requestor

VENV := .venv
COVERAGE := .coverage
BUILD := .build

export PATH := ${VENV}/bin:${PATH}

MIGRATIONS := migrations
TESTS := tests
REPORTS=reports

IMAGE_NAME := ${PROJECT}


# Installation

reports:
	@mkdir ${REPORTS}

.venv:
	@echo "Creating virtualenv...\t\t"
	poetry install --no-root
	@echo "[Installed]"

install: .venv reports

# Linters

.isort:
	@echo "Running isort checks..."
	@isort --check ${PROJECT} ${TESTS} ${MIGRATIONS}
	@echo "[Isort checks finished]"

.black:
	@echo "Running black checks..."
	@black --check --diff ${PROJECT} ${TESTS} ${MIGRATIONS}
	@echo "[Black checks finished]"

.pylint: reports
	@echo "Running pylint checks..."
	@pylint ${PROJECT} ${TESTS} ${MIGRATIONS}
	@pylint ${PROJECT} ${TESTS} ${MIGRATIONS} > ${REPORTS}/pylint.txt
	@echo "[Pylint checks finished]"

.mypy:
	@echo "Running mypy checks..."
	@mypy ${PROJECT} ${TESTS}
	@echo "[Mypy checks finished]"

.flake8:
	@echo "Running flake8 checks...\t"
	@flake8 ${PROJECT} ${TESTS} ${MIGRATIONS}
	@echo "[Flake8 checks finished]"

.bandit:
	@echo "Running bandit checks...\t"
	@bandit -q -r ${PROJECT} ${TESTS} ${MIGRATIONS} --skip B101
	@echo "[Bandit checks finished]"

.codespell:
	@echo "Running codespell checks...\t"
	@codespell ${PROJECT} ${TESTS} ${MIGRATIONS}
	@echo "[Codespell checks finished]"


# Fixers & formatters

.isort_fix:
	@echo "Fixing isort..."
	@isort ${PROJECT} ${TESTS} ${MIGRATIONS}
	@echo "[Isort fixed]"

.autopep8_fix:
	@echo "Formatting with autopep8..."
	@autopep8 --in-place -r ${PROJECT} ${TESTS} ${MIGRATIONS}
	@echo "[Autopep8 fixed]"

.black_fix:
	@echo "Formatting with black..."
	@black -q  ${PROJECT} ${TESTS} ${MIGRATIONS}
	@echo "[Black fixed]"


# Tests

.pytest:
	@echo "Running pytest checks...\t"
	@PYTHONPATH=. pytest ${TESTS} --cov=${PROJECT} --cov-report=xml

coverage: .venv reports
	@echo "Running coverage..."
	coverage run --source ${PROJECT} --module pytest
	coverage report
	coverage html -d ${REPORTS}/coverage_html
	coverage xml -o ${REPORTS}/coverage.xml -i


# Image
.build:
	mkdir -p ${BUILD}

build: .build
	docker build . -t ${IMAGE_NAME} --pull
	docker save -o ${BUILD}/${IMAGE_NAME}.tar ${IMAGE_NAME}

# Generalization

.format: .isort_fix .autopep8_fix .black_fix
format: .venv .format

.lint: .isort .black .flake8 .codespell .mypy .pylint .bandit
lint: .venv .lint

.test: .pytest
test: .venv .test


# Cleaning

clean:
	@rm -rf build dist .eggs *.egg-info
	@rm -rf ${VENV}
	@rm -rf ${REPORTS}
	@rm -rf ${BUILD}
	@find . -type d -name '.mypy_cache' -exec rm -rf {} +
	@find . -type d -name '*pytest_cache*' -exec rm -rf {} +

reinstall: clean install


.DEFAULT_GOAL = all
