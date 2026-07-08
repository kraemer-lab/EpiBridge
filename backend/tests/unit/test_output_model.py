import uuid

from app.models.output import Output


class TestOutputModel:
    def test_create_output(self):
        os_id = uuid.uuid4()
        output = Output(
            output_set_id=os_id,
            filename="summary.csv",
            size=1024,
        )
        assert output.output_set_id == os_id
        assert output.filename == "summary.csv"
        assert output.size == 1024

    def test_default_size(self):
        output = Output(
            output_set_id=uuid.uuid4(),
            filename="empty.txt",
        )
        assert output.size is None  # server_default
