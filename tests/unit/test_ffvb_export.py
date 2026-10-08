from spyke.infrastructure.ffvb.export import FfvbCalendarExportParser

HEADER = [
    "Entité",
    "Jo",
    "Match",
    "Date",
    "Heure",
    "EQA_no",
    "EQA_nom",
    "EQB_no",
    "EQB_nom",
    "Set",
    "Score",
    "Total",
    "Salle",
    "Arb1_Lic",
    "Arb1_Nom",
    "Arb1_LR",
    "Arb1_CD",
    "Arb2_Lic",
    "Arb2_Nom",
    "Arb2_LR",
    "Arb2_CD",
    "Jdl1_Lic",
    "Jdl1_Nom",
    "Jdl2_Lic",
    "Jdl2_Nom",
    "Jdl3_Lic",
    "Jdl3_Nom",
    "Jdl4_Lic",
    "Jdl4_Nom",
    "Mrq1_Lic",
    "Mrq1_Nom",
    "Mrq2_Lic",
    "Mrq2_Nom",
    "Sup_Lic",
    "Sup_Nom",
    "Slnv_Lic",
    "Slnv_Nom",
    "Vainqueur",
    "Forfait",
]
ROW = [
    "LIIDF",
    "1",
    "PMAA001",
    "2026-01-10",
    "20:00",
    "0750001",
    "AS VILLE",
    "0590002",
    "VB PARIS",
    "3/1",
    "25-20,21-25,25-22,25-18",
    "94-85",
    "Gymnase Central",
    "A1",
    "DUPONT Jean",
    "IDF",
    "75",
    "A2",
    "MARTIN Claire",
    "IDF",
    "94",
    "",
    "JUGE 1",
    "",
    "",
    "",
    "",
    "",
    "",
    "M1",
    "MARQUEUR",
    "",
    "",
    "",
    "",
    "",
    "AS VILLE",
    "",
]
PLACEHOLDER_ROW = ["LIIDF", "2", "PMAA002", "", "", "", "xxxxx", "0590002", "VB PARIS"]
EXPORT = (";".join(HEADER) + "\n" + ";".join(ROW) + "\n" + ";".join(PLACEHOLDER_ROW)).encode(
    "latin-1"
)


def test_ffvb_export_parser_preserves_structured_match_data() -> None:
    records = FfvbCalendarExportParser().parse(
        EXPORT,
        entity_code="LIIDF",
        season="2025/2026",
        source_url="https://example.test/export",
    )

    assert len(records) == 1
    record = records[0]
    assert record.pool_code == "PMAA"
    assert record.home_club_code == "0750001"
    assert record.away_team_name == "VB PARIS"
    assert record.set_scores == ((25, 20), (21, 25), (25, 22), (25, 18))
    assert record.score == (3, 1)
    assert record.referees[0].licence == "A1"
    assert record.referees[0].department == "75"
    assert record.source_url == "https://example.test/export"
