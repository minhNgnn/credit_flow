from shared.constants import REQUIRED_TAX_FILING_FIELDS
from shared.extraction.labels import match_labels
from shared.extraction.xml_tax import parse_htkk_xml

_SAMPLE_XML = b"""<?xml version="1.0"?>
<HSoThueDTu xmlns="http://kekhaithue.gdt.gov.vn/TKhaiThue">
  <HSoKhaiThue id="ID_1">
    <TTinChung>
      <TTinTKhaiThue>
        <TKhaiThue>
          <KyKKhaiThue><kieuKy>Y</kieuKy><kyKKhai>2025</kyKKhai></KyKKhaiThue>
          <maCQTNoiNop>10123</maCQTNoiNop>
          <tenCQTNoiNop>Thue co so 14 Thanh pho Ha Noi</tenCQTNoiNop>
          <ngayLapTKhai>2026-03-05</ngayLapTKhai>
        </TKhaiThue>
        <NNT>
          <mst>0110621095</mst>
          <tenNNT>CONG TY CO PHAN NTE</tenNNT>
        </NNT>
      </TTinTKhaiThue>
    </TTinChung>
    <CTieuTKhaiChinh>
      <ctE>37069517</ctE>
      <thueTNDN_tamnop_sxkd>0</thueTNDN_tamnop_sxkd>
    </CTieuTKhaiChinh>
    <PLuc>
      <PLuc_03_1A_TNDN><ct04>4374796228</ct04></PLuc_03_1A_TNDN>
    </PLuc>
  </HSoKhaiThue>
</HSoThueDTu>
"""


def test_parse_htkk_xml_returns_labelled_anchors():
    anchors = parse_htkk_xml(_SAMPLE_XML)
    texts = {a.text for a in anchors}
    assert "Mã số thuế: 0110621095" in texts
    assert "Doanh thu tính thuế: 4374796228" in texts


def test_parse_htkk_xml_output_matches_all_required_tax_fields_deterministically():
    """Đây chính là điểm mạnh của XML: tag đã tự mang ngữ nghĩa (mst,
    ngayLapTKhai, tenCQTNoiNop...) nên map sang 'Nhãn: Giá trị' xong là
    match_labels() (labels.py, không sửa gì thêm) khớp được toàn bộ, không
    cần LLM — xác minh bằng file tờ khai TNDN thật (mẫu 03/TNDN,
    2026-07-19)."""
    anchors = parse_htkk_xml(_SAMPLE_XML)
    claims = match_labels(anchors, REQUIRED_TAX_FILING_FIELDS)
    matched = {c.field_key: c.raw_value for c in claims}

    assert matched["tax_id"] == "0110621095"
    assert matched["tax_period"] == "2025"
    assert matched["tax_authority"] == "Thue co so 14 Thanh pho Ha Noi"
    assert matched["filing_date"] == "2026-03-05"
    assert matched["revenue_declared"] == "4374796228"
    assert matched["tax_payable"] == "37069517"
    assert matched["tax_paid"] == "0"


def test_parse_htkk_xml_skips_empty_elements():
    xml_with_empty = b"""<?xml version="1.0"?>
    <HSoThueDTu xmlns="http://kekhaithue.gdt.gov.vn/TKhaiThue">
      <mst>0110621095</mst>
      <ngayKy/>
    </HSoThueDTu>
    """
    anchors = parse_htkk_xml(xml_with_empty)
    assert len(anchors) == 1
    assert anchors[0].text == "Mã số thuế: 0110621095"


def test_parse_htkk_xml_ignores_unmapped_tags():
    xml_with_unknown = b"""<?xml version="1.0"?>
    <HSoThueDTu xmlns="http://kekhaithue.gdt.gov.vn/TKhaiThue">
      <mst>0110621095</mst>
      <hoanToanKhongLienQuan>abc</hoanToanKhongLienQuan>
    </HSoThueDTu>
    """
    anchors = parse_htkk_xml(xml_with_unknown)
    assert len(anchors) == 1
