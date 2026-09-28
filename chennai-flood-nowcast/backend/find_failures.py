import pytest

class FailurePrinter:
    def __init__(self):
        self.failures = []

    def pytest_runtest_logreport(self, report):
        if report.failed and report.when == 'call':
            self.failures.append(f"{report.nodeid}\n{report.longreprtext}\n{'='*50}\n")

    def save(self):
        with open("failures.txt", "w", encoding="utf-8") as f:
            f.writelines(self.failures)

if __name__ == "__main__":
    fp = FailurePrinter()
    pytest.main(['tests/'], plugins=[fp])
    fp.save()
