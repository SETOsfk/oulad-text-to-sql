import json, sqlite3, time, sys
J3 = "JOIN assessments a ON a.id_assessment=sa.id_assessment JOIN studentInfo si ON si.id_student=sa.id_student AND si.code_module=a.code_module AND si.code_presentation=a.code_presentation"
K3 = "{x}.code_module={y}.code_module AND {x}.code_presentation={y}.code_presentation AND {x}.id_student={y}.id_student"
PASS = "final_result IN ('Pass','Distinction')"
# (difficulty, tags, order_matters, question, sql)
Q = [
# ---- easy (0 join)
("easy","distinct_id",0,"How many distinct students appear in the dataset?","SELECT COUNT(DISTINCT id_student) FROM studentInfo"),
("easy","",0,"How many course presentations are there?","SELECT COUNT(*) FROM courses"),
("easy","",0,"How many enrolments ended with a Distinction?","SELECT COUNT(*) FROM studentInfo WHERE final_result='Distinction'"),
("easy","",0,"How many enrolments belong to female students?","SELECT COUNT(*) FROM studentInfo WHERE gender='F'"),
("easy","",0,"What are the distinct assessment types?","SELECT DISTINCT assessment_type FROM assessments"),
("easy","",0,"What is the average length of a course presentation in days?","SELECT AVG(module_presentation_length) FROM courses"),
("easy","",1,"How many enrolments are there in each region, from most to fewest?","SELECT region, COUNT(*) AS n FROM studentInfo GROUP BY region ORDER BY n DESC, region"),
("easy","",0,"How many enrolments are by students with a disability?","SELECT COUNT(*) FROM studentInfo WHERE disability='Y'"),
("easy","",0,"Which age band has the most enrolments?","SELECT age_band FROM studentInfo GROUP BY age_band ORDER BY COUNT(*) DESC LIMIT 1"),
("easy","null_score",0,"What is the average assessment score across all submissions?","SELECT AVG(score) FROM studentAssessment"),
("easy","",0,"How many VLE materials are forums?","SELECT COUNT(*) FROM vle WHERE activity_type='forumng'"),
("easy","",0,"What is the largest number of clicks recorded for one student on one material on one day?","SELECT MAX(sum_click) FROM studentVle"),
("easy","null",0,"How many enrolments have no IMD band recorded?","SELECT COUNT(*) FROM studentInfo WHERE imd_band IS NULL"),
("easy","",0,"How many enrolments are by students who attempted the module before?","SELECT COUNT(*) FROM studentInfo WHERE num_of_prev_attempts>=1"),
("easy","",0,"How many Exam assessments exist?","SELECT COUNT(*) FROM assessments WHERE assessment_type='Exam'"),
# ---- medium (0-2 join)
("medium","",1,"How many enrolments does each module have, from most to fewest?","SELECT code_module, COUNT(*) AS n FROM studentInfo GROUP BY code_module ORDER BY n DESC, code_module"),
("medium","pass_def",1,"What is the pass rate (Pass or Distinction, in percent, one decimal) of each module?",f"SELECT code_module, ROUND(100.0*SUM({PASS})/COUNT(*),1) FROM studentInfo GROUP BY code_module ORDER BY code_module"),
("medium","",0,"What is the withdrawal rate (percent, one decimal) for each gender?","SELECT gender, ROUND(100.0*SUM(final_result='Withdrawn')/COUNT(*),1) FROM studentInfo GROUP BY gender"),
("medium","",0,"What is the average number of studied credits for each level of highest education?","SELECT highest_education, AVG(studied_credits) FROM studentInfo GROUP BY highest_education"),
("medium","unreg",0,"How many enrolments unregistered, per module?","SELECT code_module, COUNT(*) FROM studentRegistration WHERE date_unregistration IS NOT NULL GROUP BY code_module"),
("medium","",0,"What is the average score on TMA assessments?","SELECT AVG(sa.score) FROM studentAssessment sa JOIN assessments a ON a.id_assessment=sa.id_assessment WHERE a.assessment_type='TMA'"),
("medium","",0,"What is the average Exam score for each module?","SELECT a.code_module, AVG(sa.score) FROM studentAssessment sa JOIN assessments a ON a.id_assessment=sa.id_assessment WHERE a.assessment_type='Exam' GROUP BY a.code_module"),
("medium","",0,"Which course presentation has the most assessments?","SELECT code_module, code_presentation FROM assessments GROUP BY code_module, code_presentation ORDER BY COUNT(*) DESC, code_module, code_presentation LIMIT 1"),
("medium","late",0,"How many submissions were handed in after the assessment due date?","SELECT COUNT(*) FROM studentAssessment sa JOIN assessments a ON a.id_assessment=sa.id_assessment WHERE a.date IS NOT NULL AND sa.date_submitted>a.date"),
("medium","via_assessments",0,"How many distinct students submitted at least one assessment in module BBB?","SELECT COUNT(DISTINCT sa.id_student) FROM studentAssessment sa JOIN assessments a ON a.id_assessment=sa.id_assessment WHERE a.code_module='BBB'"),
("medium","",1,"Which five VLE activity types received the most clicks in total?","SELECT v.activity_type FROM studentVle s JOIN vle v ON v.id_site=s.id_site GROUP BY v.activity_type ORDER BY SUM(s.sum_click) DESC LIMIT 5"),
("medium","",0,"How many banked submissions are there per module?","SELECT a.code_module, COUNT(*) FROM studentAssessment sa JOIN assessments a ON a.id_assessment=sa.id_assessment WHERE sa.is_banked=1 GROUP BY a.code_module"),
("medium","",0,"How many Withdrawn enrolments have a postgraduate qualification as highest education?","SELECT COUNT(*) FROM studentInfo WHERE final_result='Withdrawn' AND highest_education='Post Graduate Qualification'"),
("medium","imd_format",0,"How many enrolments are in the 10-20% IMD band?","SELECT COUNT(*) FROM studentInfo WHERE imd_band='10-20'"),
("medium","distinct_id",0,"How many distinct students ever withdrew?","SELECT COUNT(DISTINCT id_student) FROM studentInfo WHERE final_result='Withdrawn'"),
("medium","",0,"How many enrolments registered after the course had already started?","SELECT COUNT(*) FROM studentRegistration WHERE date_registration>0"),
("medium","composite_key",0,"What is the average registration day for each final result?",f"SELECT si.final_result, AVG(r.date_registration) FROM studentInfo si JOIN studentRegistration r ON {K3.format(x='si',y='r')} GROUP BY si.final_result"),
("medium","",0,"How many enrolments are there for each combination of age band and gender?","SELECT age_band, gender, COUNT(*) FROM studentInfo GROUP BY age_band, gender"),
("medium","having",1,"Which three regions with at least 1000 enrolments have the highest pass rate (Pass or Distinction)?",f"SELECT region FROM studentInfo GROUP BY region HAVING COUNT(*)>=1000 ORDER BY SUM({PASS})*1.0/COUNT(*) DESC LIMIT 3"),
("medium","",0,"Which module has the highest average number of studied credits?","SELECT code_module FROM studentInfo GROUP BY code_module ORDER BY AVG(studied_credits) DESC LIMIT 1"),
("medium","anti_join",0,"Which course presentations have no CMA assessment?","SELECT c.code_module, c.code_presentation FROM courses c WHERE NOT EXISTS (SELECT 1 FROM assessments a WHERE a.code_module=c.code_module AND a.code_presentation=c.code_presentation AND a.assessment_type='CMA')"),
("medium","",0,"How many quiz materials does each module have?","SELECT code_module, COUNT(*) FROM vle WHERE activity_type='quiz' GROUP BY code_module"),
("medium","",0,"How many enrolments by students with a disability ended with a Distinction?","SELECT COUNT(*) FROM studentInfo WHERE disability='Y' AND final_result='Distinction'"),
# ---- hard (3+ tables, subqueries, windows)
("hard","3table_composite",0,"What is the average assessment score for each final result?",f"SELECT si.final_result, AVG(sa.score) FROM studentAssessment sa {J3} GROUP BY si.final_result"),
("hard","subquery",0,"What is the average total number of clicks per student in module AAA, presentation 2013J?","SELECT AVG(t) FROM (SELECT SUM(sum_click) AS t FROM studentVle WHERE code_module='AAA' AND code_presentation='2013J' GROUP BY id_student)"),
("hard","not_exists",0,"How many withdrawn enrolments never submitted any assessment?","WITH sub AS (SELECT DISTINCT a.code_module, a.code_presentation, sa.id_student FROM studentAssessment sa JOIN assessments a ON a.id_assessment=sa.id_assessment) SELECT COUNT(*) FROM studentInfo si LEFT JOIN sub ON sub.code_module=si.code_module AND sub.code_presentation=si.code_presentation AND sub.id_student=si.id_student WHERE si.final_result='Withdrawn' AND sub.id_student IS NULL"),
("hard","imd_format",1,"What is the pass rate (Pass or Distinction, percent, one decimal) for each IMD band, ignoring missing bands, ordered by band?",f"SELECT imd_band, ROUND(100.0*SUM({PASS})/COUNT(*),1) FROM studentInfo WHERE imd_band IS NOT NULL GROUP BY imd_band ORDER BY imd_band"),
("hard","",1,"Who are the five students with the most total clicks in module FFF, presentation 2014J?","SELECT id_student FROM studentVle WHERE code_module='FFF' AND code_presentation='2014J' GROUP BY id_student ORDER BY SUM(sum_click) DESC, id_student LIMIT 5"),
("hard","3table_composite",0,"What is the average TMA score for each module among students who passed or got a Distinction?",f"SELECT a.code_module, AVG(sa.score) FROM studentAssessment sa {J3} WHERE a.assessment_type='TMA' AND si.{PASS} GROUP BY a.code_module"),
("hard","",0,"How many distinct students used forum materials in module DDD, presentation 2013J?","SELECT COUNT(DISTINCT s.id_student) FROM studentVle s JOIN vle v ON v.id_site=s.id_site WHERE v.activity_type='forumng' AND s.code_module='DDD' AND s.code_presentation='2013J'"),
("hard","subquery_join",0,"In presentation 2014J, what is the average total number of clicks per student for each final result?","SELECT final_result, AVG(t) FROM (SELECT si.final_result, SUM(s.sum_click) AS t FROM studentVle s JOIN studentInfo si ON si.code_module=s.code_module AND si.code_presentation=s.code_presentation AND si.id_student=s.id_student WHERE s.code_presentation='2014J' GROUP BY s.code_module, s.id_student) GROUP BY final_result"),
("hard","",0,"How many distinct students scored 90 or more in an Exam?","SELECT COUNT(DISTINCT sa.id_student) FROM studentAssessment sa JOIN assessments a ON a.id_assessment=sa.id_assessment WHERE a.assessment_type='Exam' AND sa.score>=90"),
("hard","",0,"For each module, what percentage of enrolments unregistered before the course started?","SELECT code_module, ROUND(100.0*SUM(date_unregistration<0)/COUNT(*),2) FROM studentRegistration GROUP BY code_module"),
("hard","cte",0,"Which modules have a higher average CMA score than TMA score?","WITH m AS (SELECT a.code_module, a.assessment_type t, AVG(sa.score) s FROM studentAssessment sa JOIN assessments a ON a.id_assessment=sa.id_assessment GROUP BY 1,2) SELECT c.code_module FROM m c JOIN m t ON t.code_module=c.code_module AND t.t='TMA' WHERE c.t='CMA' AND c.s>t.s"),
("hard","distinct_id",0,"How many enrolments belong to students who enrolled in more than one course presentation?","SELECT COUNT(*) FROM studentInfo WHERE id_student IN (SELECT id_student FROM studentInfo GROUP BY id_student HAVING COUNT(*)>1)"),
("hard","",0,"How many distinct students ever scored exactly 100 on an assessment?","SELECT COUNT(DISTINCT id_student) FROM studentAssessment WHERE score=100"),
("hard","having",0,"Which modules have more than 1000 withdrawn enrolments?","SELECT code_module FROM studentInfo WHERE final_result='Withdrawn' GROUP BY code_module HAVING COUNT(*)>1000"),
("hard","late",0,"What is the late-submission rate (percent, one decimal) for each assessment type, among assessments with a due date?","SELECT a.assessment_type, ROUND(100.0*SUM(sa.date_submitted>a.date)/COUNT(*),1) FROM studentAssessment sa JOIN assessments a ON a.id_assessment=sa.id_assessment WHERE a.date IS NOT NULL GROUP BY a.assessment_type"),
("hard","join_chain",0,"In presentation 2014J, which VLE activity type had the most distinct students interacting with it?","SELECT v.activity_type FROM studentVle s JOIN vle v ON v.id_site=s.id_site WHERE s.code_presentation='2014J' GROUP BY v.activity_type ORDER BY COUNT(DISTINCT s.id_student) DESC LIMIT 1"),
("hard","",1,"What is the pass rate (Pass or Distinction, percent, one decimal) for each highest education level, from highest to lowest?",f"SELECT highest_education, ROUND(100.0*SUM({PASS})/COUNT(*),1) AS r FROM studentInfo GROUP BY highest_education ORDER BY r DESC"),
("hard","3table_composite",0,"How many enrolments failed the Exam (score below 40) but still passed the course?",f"SELECT COUNT(DISTINCT si.code_module||si.code_presentation||si.id_student) FROM studentAssessment sa {J3} WHERE a.assessment_type='Exam' AND sa.score<40 AND si.{PASS}"),
("hard","relational_division",0,"In module BBB, presentation 2013J, how many students submitted every TMA?","SELECT COUNT(*) FROM (SELECT sa.id_student FROM studentAssessment sa JOIN assessments a ON a.id_assessment=sa.id_assessment WHERE a.code_module='BBB' AND a.code_presentation='2013J' AND a.assessment_type='TMA' GROUP BY sa.id_student HAVING COUNT(DISTINCT a.id_assessment)=(SELECT COUNT(*) FROM assessments WHERE code_module='BBB' AND code_presentation='2013J' AND assessment_type='TMA'))"),
("easy","",0,"What is the total number of clicks recorded in the dataset?","SELECT SUM(sum_click) FROM studentVle"),
("medium","",0,"How many enrolments did each presentation of module DDD have?","SELECT code_presentation, COUNT(*) FROM studentInfo WHERE code_module='DDD' GROUP BY code_presentation"),
("hard","window",0,"For each module, which assessment has the highest average score?","SELECT code_module, id_assessment FROM (SELECT a.code_module, a.id_assessment, ROW_NUMBER() OVER (PARTITION BY a.code_module ORDER BY AVG(sa.score) DESC) rn FROM studentAssessment sa JOIN assessments a ON a.id_assessment=sa.id_assessment GROUP BY a.code_module, a.id_assessment) WHERE rn=1"),
]
con = sqlite3.connect("oulad.db")
out = []
for i,(d,tags,om,qu,sql) in enumerate(Q,1):
    t=time.time(); rows=con.execute(sql).fetchall(); dt=time.time()-t
    nj = sql.upper().count(" JOIN ")
    print(f"Q{i:02d} {d:6} {dt:5.1f}s n={len(rows):3} {str(rows[:2])[:90]}  | {qu[:50]}")
    out.append(dict(id=f"q{i:02d}",difficulty=d,tags=[x for x in tags.split(',') if x],order_matters=bool(om),n_joins=nj,question=qu,gold_sql=sql))
print(len(Q), {d:sum(1 for q in out if q['difficulty']==d) for d in ('easy','medium','hard')})
json.dump(out, open("questions_draft.json","w"), ensure_ascii=False, indent=1)
