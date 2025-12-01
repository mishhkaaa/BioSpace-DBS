import pandas as pd
import json

# Check missing papers
df = pd.read_csv('data_prep/cleaned_80.csv')
print(f'Total rows: {len(df)}')
print(f'Missing abstracts: {df["abstract"].isna().sum()}')

missing = df[df["abstract"].isna()]
print('\nPapers with missing abstracts:')
for _, row in missing.iterrows():
    print(f'  {row["paper_id"]}: {row["title"][:70]}...')

# Entity analysis
print('\n' + '='*70)
print('ENTITY FREQUENCY ANALYSIS')
print('='*70)

entities = json.load(open('graph_data/entities.json', 'r', encoding='utf-8'))
stats = sorted([{'name': e['name'], 'type': e['type'], 'papers': len(e['papers'])} for e in entities], 
               key=lambda x: x['papers'], reverse=True)

print(f'\nTop 20 most frequent entities:')
for i, s in enumerate(stats[:20]):
    print(f'{i+1:2d}. {s["name"]:35s} ({s["type"]:12s}) - {s["papers"]} papers')

single = sum(1 for s in stats if s['papers'] == 1)
print(f'\n📊 STATISTICS:')
print(f'   Total unique entities: {len(entities)}')
print(f'   Entities in only 1 paper: {single} ({single/len(entities)*100:.1f}%)')
print(f'   Entities in 2+ papers: {len(entities) - single}')
print(f'   Entities in 3+ papers: {sum(1 for s in stats if s["papers"] >= 3)}')
print(f'   Entities in 5+ papers: {sum(1 for s in stats if s["papers"] >= 5)}')
print(f'   Entities in 10+ papers: {sum(1 for s in stats if s["papers"] >= 10)}')

# Suggest filtering threshold
print(f'\n💡 RECOMMENDATION:')
print(f'   If we filter to entities appearing in 2+ papers: {len(entities) - single} entities')
print(f'   If we filter to entities appearing in 3+ papers: {sum(1 for s in stats if s["papers"] >= 3)} entities')
print(f'   If we filter to entities appearing in 5+ papers: {sum(1 for s in stats if s["papers"] >= 5)} entities')
