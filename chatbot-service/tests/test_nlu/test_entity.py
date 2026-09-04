"""实体抽取器单元测试。"""
from nlu.entity_extractor import EntityExtractor


class TestEntityExtractor:
    def setup_method(self):
        self.extractor = EntityExtractor()

    def test_extract_date(self):
        entities = self.extractor.extract_by_rule("请查一下 2024-06-01 的订单")
        dates = [e for e in entities if e.type == "date"]
        assert len(dates) >= 1
        assert dates[0].value == "2024-06-01"

    def test_extract_phone(self):
        entities = self.extractor.extract_by_rule("我的手机号是 13812345678")
        phones = [e for e in entities if e.type == "phone"]
        assert len(phones) == 1
        assert phones[0].value == "13812345678"

    def test_extract_email(self):
        entities = self.extractor.extract_by_rule("邮箱是 test@example.com")
        emails = [e for e in entities if e.type == "email"]
        assert len(emails) == 1
        assert emails[0].value == "test@example.com"

    def test_no_entities(self):
        entities = self.extractor.extract_by_rule("今天天气真好")
        assert len(entities) == 0
