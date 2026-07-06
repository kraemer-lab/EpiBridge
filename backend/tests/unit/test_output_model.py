import uuid

from app.models.output import Output


class TestOutputModel:
    def test_create_output(self):
        er_id = uuid.uuid4()
        output = Output(
            execution_request_id=er_id,
            filename="summary.csv",
            size=1024,
        )
        assert output.execution_request_id == er_id
        assert output.filename == "summary.csv"
        assert output.size == 1024

    def test_default_status(self):
        output = Output(
            execution_request_id=uuid.uuid4(),
            filename="output.txt",
            size=512,
        )
        assert output.status is None  # server_default

    def test_default_size(self):
        output = Output(
            execution_request_id=uuid.uuid4(),
            filename="empty.txt",
        )
        assert output.size is None  # server_default
