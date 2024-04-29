from process_logic import process_logic
from robocorp.tasks import task


@task
def main():
    process = process_logic()


# @task
# def handle_item():
#     item = workitems.inputs.current
#     print("Received payload:", item.payload)
#     workitems.outputs.create(payload={"key": "value"})