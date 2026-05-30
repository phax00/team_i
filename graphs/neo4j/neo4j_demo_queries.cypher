// 1. Quick sanity check: total counts
MATCH (n)
RETURN count(n) AS node_count;

MATCH ()-[r]->()
RETURN count(r) AS relationship_count;


// 2. Node counts by label
MATCH (n)
UNWIND labels(n) AS label
RETURN label, count(*) AS count
ORDER BY count DESC, label;


// 3. Find people with their role and country
MATCH (p:Person)-[:HAS_ROLE]->(r:Role)
OPTIONAL MATCH (p)-[:LOCATED_IN]->(c:Country)
RETURN p.name AS person, r.name AS role, c.name AS country
ORDER BY person;


// 4. Find experts by skill
MATCH (p:Person)-[:HAS_SKILL]->(s:Skill)
WHERE toLower(s.name) CONTAINS "ifs"
RETURN p.name AS person, s.name AS skill
ORDER BY person;


// 5. Find people by topic ownership
MATCH (p:Person)-[:OWNS_TOPIC]->(t:Topic)
WHERE toLower(t.name) CONTAINS "planning"
RETURN p.name AS person, t.name AS topic
ORDER BY person;


// 6. People, their manager, and their team
MATCH (p:Person)
OPTIONAL MATCH (p)-[:REPORTS_TO]->(m:Person)
OPTIONAL MATCH (p)-[:MEMBER_OF]->(team:Team)
RETURN p.name AS person, m.name AS manager, team.name AS team
ORDER BY person;


// 7. Job descriptions and required baseline skills
MATCH (jd:JobDescription)-[:REQUIRES_SKILL]->(s:Skill)
RETURN jd.name AS job_description, collect(s.name) AS required_skills
ORDER BY job_description;


// 8. Role -> JD -> department context
MATCH (r:Role)-[:DESCRIBED_BY]->(jd:JobDescription)
OPTIONAL MATCH (r)-[:BELONGS_TO_DEPARTMENT]->(d:Department)
RETURN r.name AS role, jd.name AS job_description, d.name AS department
ORDER BY role;


// 9. Site and country coverage
MATCH (site:Site)-[:IN_COUNTRY]->(country:Country)
RETURN site.name AS site, country.name AS country
ORDER BY country, site;


// 10. Simple path exploration for a concrete person
MATCH (p:Person {name: "Erik Sykora"})
OPTIONAL MATCH (p)-[:HAS_ROLE]->(r:Role)
OPTIONAL MATCH (p)-[:LOCATED_IN]->(c:Country)
OPTIONAL MATCH (p)-[:MEMBER_OF]->(team:Team)
OPTIONAL MATCH (p)-[:KNOWS_SYSTEM]->(sys:System)
OPTIONAL MATCH (p)-[:OWNS_TOPIC]->(topic:Topic)
RETURN
  p.name AS person,
  r.name AS role,
  c.name AS country,
  team.name AS team,
  collect(DISTINCT sys.name) AS systems,
  collect(DISTINCT topic.name) AS topics;
