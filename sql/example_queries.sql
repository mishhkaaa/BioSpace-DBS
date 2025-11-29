-- sql/example_queries.sql
-- Microstep 13: Insightful SQL Queries for DBMS Report and Dashboard

-- 1. Get top 15 most frequent keywords across the corpus
SELECT k.text AS keyword,
       COUNT(pk.paper_id) AS papers_using_keyword,
       AVG(k.score) AS avg_score
FROM keywords k
JOIN paper_keyword pk ON pk.keyword_id = k.id
GROUP BY k.text
ORDER BY papers_using_keyword DESC
LIMIT 15;

-- 2. Distribution of papers per cluster
SELECT c.label AS cluster_id,
       COUNT(pc.paper_id) AS num_papers
FROM clusters c
JOIN paper_cluster pc ON pc.cluster_id = c.id
GROUP BY c.label
ORDER BY num_papers DESC;

-- 3. Papers whose summary mentions "microgravity"
SELECT p.title, s.text
FROM papers p
JOIN summaries s ON p.id = s.paper_id
WHERE s.text LIKE '%microgravity%';

-- 4. Average keyword score per cluster
SELECT c.label AS cluster_id,
       AVG(k.score) AS avg_keyword_score
FROM clusters c
JOIN paper_cluster pc ON pc.cluster_id = c.id
JOIN paper_keyword pk ON pk.paper_id = pc.paper_id
JOIN keywords k ON k.id = pk.keyword_id
GROUP BY c.label
ORDER BY avg_keyword_score ASC;

-- 5. List papers published after 2015 grouped by cluster
SELECT p.year,
       c.label AS cluster_id,
       COUNT(*) AS num_papers
FROM papers p
JOIN paper_cluster pc ON pc.paper_id = p.id
JOIN clusters c ON c.id = pc.cluster_id
WHERE p.year >= 2015
GROUP BY p.year, c.label
ORDER BY p.year, cluster_id;
