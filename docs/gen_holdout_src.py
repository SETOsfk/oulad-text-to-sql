import json, sqlite3, time
J3 = "JOIN assessments a ON a.id_assessment=sa.id_assessment JOIN studentInfo si ON si.id_student=sa.id_student AND si.code_module=a.code_module AND si.code_presentation=a.code_presentation"
K = "{x}.code_module={y}.code_module AND {x}.code_presentation={y}.code_presentation AND {x}.id_student={y}.id_student"
H = [
("easy","value",0,"How many enrolments are by students aged 55 or over?","SELECT COUNT(*) FROM studentInfo WHERE age_band='55<='"),
("easy","value",0,"How many enrolments are by students with no formal qualifications?","SELECT COUNT(*) FROM studentInfo WHERE highest_education='No Formal quals'"),
("easy","value",0,"How many computer-marked assessments (CMA) are there?","SELECT COUNT(*) FROM assessments WHERE assessment_type='CMA'"),
("medium","value",0,"How many enrolments from Wales ended in Fail?","SELECT COUNT(*) FROM studentInfo WHERE region='Wales' AND final_result='Fail'"),
("medium","",0,"Which VLE activity type has the most materials?","SELECT activity_type FROM vle GROUP BY activity_type ORDER BY COUNT(*) DESC LIMIT 1"),
("medium","value",0,"How many oucontent materials does each module have?","SELECT code_module, COUNT(*) FROM vle WHERE activity_type='oucontent' GROUP BY code_module"),
("medium","value",0,"How many enrolments are in the 90-100% IMD band?","SELECT COUNT(*) FROM studentInfo WHERE imd_band='90-100%'"),
("medium","",0,"What is the average score of CMA submissions for each module?","SELECT a.code_module, AVG(sa.score) FROM studentAssessment sa JOIN assessments a ON a.id_assessment=sa.id_assessment WHERE a.assessment_type='CMA' GROUP BY a.code_module"),
("medium","value",0,"How many enrolments are by students whose highest education is below A level?","SELECT COUNT(*) FROM studentInfo WHERE highest_education='Lower Than A Level'"),
("hard","composite",0,"What is the average assessment score of students with a disability?",f"SELECT AVG(sa.score) FROM studentAssessment sa {J3} WHERE si.disability='Y'"),
("hard","composite",0,"How many enrolments never clicked on any VLE material?","SELECT COUNT(*) FROM studentInfo si WHERE NOT EXISTS (SELECT 1 FROM studentVle s WHERE s.code_module=si.code_module AND s.code_presentation=si.code_presentation AND s.id_student=si.id_student)"),
("hard","composite",0,"What is the average total number of clicks per enrolment for enrolments that ended in Fail?","SELECT AVG(t) FROM (SELECT SUM(s.sum_click) t FROM studentVle s JOIN studentInfo si ON si.code_module=s.code_module AND si.code_presentation=s.code_presentation AND si.id_student=s.id_student WHERE si.final_result='Fail' GROUP BY s.code_module, s.code_presentation, s.id_student)"),
("hard","composite",0,"How many enrolments that unregistered had submitted at least one assessment?","WITH sub AS (SELECT DISTINCT a.code_module, a.code_presentation, sa.id_student FROM studentAssessment sa JOIN assessments a ON a.id_assessment=sa.id_assessment) SELECT COUNT(*) FROM studentRegistration r JOIN sub ON sub.code_module=r.code_module AND sub.code_presentation=r.code_presentation AND sub.id_student=r.id_student WHERE r.date_unregistration IS NOT NULL"),
("medium","",0,"How many female enrolments aged 0-35 are there for each final result?","SELECT final_result, COUNT(*) FROM studentInfo WHERE gender='F' AND age_band='0-35' GROUP BY final_result"),
("hard","composite",0,"What is the average TMA score of Distinction students in module CCC?",f"SELECT AVG(sa.score) FROM studentAssessment sa {J3} WHERE a.assessment_type='TMA' AND a.code_module='CCC' AND si.final_result='Distinction'"),
("medium","",0,"What is the earliest registration day in each module?","SELECT code_module, MIN(date_registration) FROM studentRegistration GROUP BY code_module"),
("hard","",0,"Which module has the highest withdrawal rate?","SELECT code_module FROM studentInfo GROUP BY code_module ORDER BY SUM(final_result='Withdrawn')*1.0/COUNT(*) DESC LIMIT 1"),
("hard","composite",0,"How many distinct students in module FFF, presentation 2013J clicked on a quiz?","SELECT COUNT(DISTINCT s.id_student) FROM studentVle s JOIN vle v ON v.id_site=s.id_site WHERE s.code_module='FFF' AND s.code_presentation='2013J' AND v.activity_type='quiz'"),
("hard","composite",0,"How many students have an Exam score recorded in module CCC, presentation 2014J?","SELECT COUNT(DISTINCT sa.id_student) FROM studentAssessment sa JOIN assessments a ON a.id_assessment=sa.id_assessment WHERE a.assessment_type='Exam' AND a.code_module='CCC' AND a.code_presentation='2014J' AND sa.score IS NOT NULL"),
("medium","",0,"What percentage of enrolments with a disability ended in Withdrawn (one decimal)?","SELECT ROUND(100.0*SUM(final_result='Withdrawn')/COUNT(*),1) FROM studentInfo WHERE disability='Y'"),
]
con=sqlite3.connect("oulad.db"); out=[]
for i,(d,tags,om,q,sql) in enumerate(H,1):
    t=time.time(); rows=con.execute(sql).fetchall()
    print(f"h{i:02d} {d:6} {time.time()-t:4.1f}s n={len(rows)} {str(rows[:2])[:70]} | {q[:48]}")
    out.append(dict(id=f"h{i:02d}",difficulty=d,tags=[x for x in tags.split(',') if x],order_matters=bool(om),n_joins=sql.upper().count(" JOIN "),question=q,gold_sql=sql))
dst="/sessions/rcw-01kauesj6x5derbrrccp6ozw/mnt/Sertan_Safak_CV/Projeler/oulad-text-to-sql/"
open(dst+"questions_holdout.jsonl","w").write("\n".join(json.dumps(x,ensure_ascii=False) for x in out)+"\n")
A = [
("How many students passed?","enrolments vs distinct students; Pass only or Pass+Distinction"),
("What is the average score?","which assessments (TMA/CMA/Exam), which module"),
("Which region is the best?","'best' by what metric"),
("How many students dropped out?","Withdrawn result vs unregistration date differ (10,156 vs 10,072)"),
("Show me the most active students.","active by clicks, submissions or both; which course"),
("How many students are there in 2014?","presentations 2014B and 2014J; students vs enrolments"),
("What is the failure rate?","Fail only or Fail+Withdrawn; overall or per module"),
("Which module is the hardest?","hardest by fail rate, score, withdrawal?"),
("How many students are disadvantaged?","disadvantaged is not defined; IMD band threshold"),
("How long do students take to submit?","relative to due date or course start; which assessments"),
]
open(dst+"questions_ambiguous.jsonl","w").write("\n".join(json.dumps(dict(id=f"a{i:02d}",question=q,why_ambiguous=w),ensure_ascii=False) for i,(q,w) in enumerate(A,1))+"\n")
