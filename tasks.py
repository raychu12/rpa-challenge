from process_logic import process_logic
from robocorp.tasks import task


@task
def main():
    process = process_logic()