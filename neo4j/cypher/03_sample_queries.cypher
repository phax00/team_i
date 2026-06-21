// Count imported graph size.
MATCH (n)
RETURN count(n) AS nodes;

MATCH ()-[r]->()
RETURN count(r) AS relationships;

// Label distribution.
MATCH (n)
RETURN labels(n)[0] AS label, count(n) AS count
ORDER BY count DESC, label;

// Relationship distribution.
MATCH ()-[r]->()
RETURN type(r) AS relationship_type, count(r) AS count
ORDER BY count DESC, relationship_type;

// Who is the COO?
MATCH (p:Person)-[:HAS_ROLE]->(r:Role)
WHERE toLower(r.name) CONTAINS "chief operating officer"
RETURN p.name AS person, r.name AS role;

// Who reports to the COO?
MATCH (report:Person)-[:REPORTS_TO]->(manager:Person)-[:HAS_ROLE]->(role:Role)
WHERE toLower(role.name) CONTAINS "chief operating officer"
RETURN report.name AS direct_report, manager.name AS manager, role.name AS manager_role
ORDER BY direct_report;

// Who works in Slovakia?
MATCH (p:Person)-[:LOCATED_IN]->(c:Country {name: "Slovakia"})
RETURN p.name AS person, c.name AS country
ORDER BY person;

// Who knows ERP?
MATCH (p:Person)-[:KNOWS_SYSTEM]->(s:System {name: "ERP"})
RETURN p.name AS person, s.name AS system
ORDER BY person;

// Relationship path example.
MATCH path = shortestPath((a:Person {name: "Petra Novakova"})-[*..4]-(b:Person {name: "Filip Hruby"}))
RETURN path;
