import os

def search_rules(query: str, rules_file_path: str) -> str:
    """
    Simple keyword search in the rules file.
    Returns paragraphs containing the query.
    """
    if not os.path.exists(rules_file_path):
        return "Rules file not found."
        
    query = query.lower()
    results = []
    
    with open(rules_file_path, "r") as f:
        content = f.read()
        
    # Split by paragraphs (approximate with double newline)
    paragraphs = content.split("\n\n")
    
    for p in paragraphs:
        if query in p.lower():
            results.append(p)
            
    if not results:
        return f"No rules found regarding '{query}'."
        
    return "\n---\n".join(results[:3]) # Return top 3 matches
