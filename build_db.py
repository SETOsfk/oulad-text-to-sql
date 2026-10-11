"""CSV'leri (OULAD, CC BY 4.0) tipli, anahtarlı bir SQLite'a yükler: python build_db.py"""
import csv, os, sqlite3, pathlib

SRC = pathlib.Path("data/archive")
DB = pathlib.Path(os.environ.get("OULAD_DB", "data/oulad.db"))  # ponytail: bağlı klasörde SQLite kilitleme hatası verir, OULAD_DB ile dışarı al
EXPECTED = {"courses": 22, "assessments": 206, "vle": 6364, "studentInfo": 32593,
            "studentRegistration": 32593, "studentAssessment": 173912, "studentVle": 10655280}

SCHEMA = """
CREATE TABLE courses (code_module TEXT, code_presentation TEXT, module_presentation_length INTEGER,
  PRIMARY KEY (code_module, code_presentation));
CREATE TABLE assessments (id_assessment INTEGER PRIMARY KEY, code_module TEXT, code_presentation TEXT,
  assessment_type TEXT, date INTEGER, weight REAL,
  FOREIGN KEY (code_module, code_presentation) REFERENCES courses);
CREATE TABLE vle (id_site INTEGER PRIMARY KEY, code_module TEXT, code_presentation TEXT,
  activity_type TEXT, week_from INTEGER, week_to INTEGER,
  FOREIGN KEY (code_module, code_presentation) REFERENCES courses);
CREATE TABLE studentInfo (code_module TEXT, code_presentation TEXT, id_student INTEGER, gender TEXT,
  region TEXT, highest_education TEXT, imd_band TEXT, age_band TEXT, num_of_prev_attempts INTEGER,
  studied_credits INTEGER, disability TEXT, final_result TEXT,
  PRIMARY KEY (code_module, code_presentation, id_student),
  FOREIGN KEY (code_module, code_presentation) REFERENCES courses);
CREATE TABLE studentRegistration (code_module TEXT, code_presentation TEXT, id_student INTEGER,
  date_registration INTEGER, date_unregistration INTEGER,
  PRIMARY KEY (code_module, code_presentation, id_student));
CREATE TABLE studentAssessment (id_assessment INTEGER, id_student INTEGER, date_submitted INTEGER,
  is_banked INTEGER, score REAL, PRIMARY KEY (id_assessment, id_student),
  FOREIGN KEY (id_assessment) REFERENCES assessments);
CREATE TABLE studentVle (code_module TEXT, code_presentation TEXT, id_student INTEGER, id_site INTEGER,
  date INTEGER, sum_click INTEGER, FOREIGN KEY (id_site) REFERENCES vle);
"""
# bağımlılık sırası: FK hedefleri önce
ORDER = ["courses", "assessments", "vle", "studentInfo", "studentRegistration", "studentAssessment", "studentVle"]

def main():
    DB.unlink(missing_ok=True)
    con = sqlite3.connect(DB)
    con.executescript(SCHEMA)
    for t in ORDER:
        with open(SRC / f"{t}.csv", newline="", encoding="utf-8") as f:
            r = csv.reader(f); cols = next(r)  # kolon sırası CSV başlığından (assessments'ta farklı)
            rows = ([None if v == "" else v for v in row] for row in r)  # boş = NULL
            con.executemany(f"INSERT INTO {t} ({','.join(cols)}) VALUES ({','.join('?'*len(cols))})", rows)
        got = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        assert got == EXPECTED[t], (t, got, EXPECTED[t])  # makaledeki satır sayılarıyla eşleşmeli
        print(t, got)
    con.execute("CREATE INDEX ix_svle_student ON studentVle(code_module, code_presentation, id_student)")
    con.execute("CREATE INDEX ix_svle_site ON studentVle(id_site)")
    con.commit(); con.close()

if __name__ == "__main__":
    main()
