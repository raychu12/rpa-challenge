from process_logic import ProcessLogic
from robocorp.tasks import task


@task
def main():
    process = ProcessLogic()