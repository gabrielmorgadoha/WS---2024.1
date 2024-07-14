from rdflib import Graph, Namespace, RDF
from rdflib.namespace import NamespaceManager
from pyshacl import validate
import re
import time

EX = Namespace("http://example.org/ns#")
XSD = Namespace("http://www.w3.org/2001/XMLSchema#")
SH = Namespace("http://www.w3.org/ns/shacl#")

shapes_graph = Graph()
shapes_graph.parse("shacl.ttl")

shapes_graph.namespace_manager.bind("ex", EX)
shapes_graph.namespace_manager.bind("xsd", XSD)
shapes_graph.namespace_manager.bind("sh", SH)

data_graph = Graph()
data_graph.parse("rdfGraph.ttl")

def optimize_sparql_query(query, shapes_graph):
    optimized_query = query

    shapes = shapes_graph.subjects(RDF.type, SH.NodeShape)
    for shape in shapes:
        target_class = shapes_graph.value(shape, SH.targetClass)
        properties = shapes_graph.objects(shape, SH.property)
        
        for prop in properties:
            path_full = shapes_graph.value(prop, SH.path)
            max_count = shapes_graph.value(prop, SH.maxCount)
            min_count = shapes_graph.value(prop, SH.minCount)
            datatype_full = shapes_graph.value(prop, SH.datatype)
            lang_matches = shapes_graph.value(prop, SH.langMatches)
            min_exclusive = shapes_graph.value(prop, SH.minExclusive)
            min_inclusive = shapes_graph.value(prop, SH.minInclusive)
            max_exclusive = shapes_graph.value(prop, SH.maxExclusive)
            max_inclusive = shapes_graph.value(prop, SH.maxInclusive)

            path = shapes_graph.namespace_manager.normalizeUri(path_full)
            datatype = shapes_graph.namespace_manager.normalizeUri(datatype_full)

            if min_count and max_count:
                pattern = r'OPTIONAL\s*{\s*(\?\w+)\s*' + re.escape(str(path)) + r'\s*(\?\w+)\s*.?\s*}'
                replacement = r'\1 ' + str(path) + r' \2 '
                optimized_query = re.sub(pattern, replacement, optimized_query)
            
            if datatype:
                pattern = r'FILTER\s*\(\s*datatype\s*\(\s*\?\w+\s*\)\s*=\s*' + re.escape(str(datatype)) + r'\s*\)\s*.?\s*'
                replacement = ''
                optimized_query = re.sub(pattern, replacement, optimized_query)
                
            if lang_matches: 
                pattern = r'FILTER\s*\(\s*langMatches\s*\(\s*lang\s*\(\?\w+\s*\)\s*=\s*"' + re.escape(str(lang_matches)) + r'"\s*\)\s*.?\s*'
                replacement = ''
                optimized_query = re.sub(pattern, replacement, optimized_query)
            
            if max_count:
                pattern = r'OPTIONAL\s*{\s*(\?\w+)\s*' + re.escape(str(path)) + r'\s*(\?\w+)\s*.?\s*}'
                replacement = r'\1 ' + str(path) + r' \2 .'
                optimized_query = re.sub(pattern, replacement, optimized_query)
            
            if min_count:
                pattern = r'OPTIONAL\s*{\s*(\?\w+)\s*' + re.escape(str(path)) + r'\s*(\?\w+)\s*.?\s*}'
                replacement = r'\1 ' + str(path) + r' \2 .'
                optimized_query = re.sub(pattern, replacement, optimized_query)
				
            if min_exclusive:
                pattern = r'(?i)HAVING\s*(\(min\s*\(\?' + re.escape(str(path).split(':')[1]) + r'\)\s*>\s*\d+\s*\))'
                replacement = ''
                optimized_query = re.sub(pattern, replacement, optimized_query)

            if min_inclusive:
                pattern = r'(?i)HAVING\s*(\(min\s*\(\?' + re.escape(str(path).split(':')[1]) + r'\)\s*>=\s*\d+\s*\))'
                replacement = ''
                optimized_query = re.sub(pattern, replacement, optimized_query)

            if max_exclusive:
                pattern = r'(?i)HAVING\s*(\(min\s*\(\?' + re.escape(str(path).split(':')[1]) + r'\)\s*<\s*\d+\s*\))'
                replacement = ''
                optimized_query = re.sub(pattern, replacement, optimized_query)

            if max_inclusive:
                pattern = r'(?i)HAVING\s*(\(min\s*\(\?' + re.escape(str(path).split(':')[1]) + r'\)\s*<=\s*\d+\s*\))'
                replacement = ''
                optimized_query = re.sub(pattern, replacement, optimized_query)
    
    return optimized_query

original_query = """
PREFIX ex: <http://example.org/ns#>
PREFIX sh: <http://www.w3.org/ns/shacl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?name ?mbox
WHERE {
  ?subject ex:name ?name .
  ?subject ex:age ?age .
  ?subject ex:mbox ?mbox .
  FILTER (datatype(?mbox)=xsd:string) .
  FILTER regex(str(?mbox), "work", "i") .
  FILTER (?age > 40) .
}
"""

conforms, results_graph, results_text = validate(data_graph, shacl_graph=shapes_graph, inference='rdfs')
if conforms:
    print("Os dados RDF estão respeitando as restrições SHACL.")
else:
    print("Os dados RDF violam as restrições SHACL.")

print("\n-----------------------------")
    
optimized_query = optimize_sparql_query(original_query, shapes_graph)

# Query feita antes para carregar grafo previamente
# Evita viés de tempo depois
original_res = data_graph.query(original_query)

print("\nQuery original:")
print(original_query)
ori_start_time = time.time()
original_res = data_graph.query(original_query)
ori_end_time = time.time()
print("name    | mbox")
for row in original_res:
    print(f"{row.name} | {row.mbox}")

print("\n-----------------------------")
    
print("\nQuery otimizada:")
print(optimized_query)
opt_start_time = time.time()
optimized_res = data_graph.query(optimized_query)
opt_end_time = time.time()
print("name    | mbox")
for row in optimized_res:
    print(f"{row.name} | {row.mbox}")

print(f"\nTempo original: {ori_end_time - ori_start_time} segundos")
print(f"Tempo otimizado: {opt_end_time - opt_start_time} segundos")
