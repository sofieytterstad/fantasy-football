import re
import glob

# Pattern to match the simplified through structure
pattern = r'(    through:\n      property: (\w+))'

# Files to process
files = glob.glob('modules/fantasy-football/data_models/views/*.yaml')

for filepath in files:
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Find the view/source details from earlier in the file
    # We need to extract externalId from source sections
    
    # Find all reverse relations and fix them
    lines = content.split('\n')
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Check if this line starts a reverse relation with simplified through
        if '    through:' in line and i+1 < len(lines) and '      property:' in lines[i+1]:
            # Get the property name
            property_match = re.search(r'property: (\w+)', lines[i+1])
            if property_match:
                property_name = property_match.group(1)
                
                # Look back to find the source externalId
                for j in range(i-1, max(0, i-10), -1):
                    if '      externalId:' in lines[j]:
                        source_id_match = re.search(r'externalId: (\w+)', lines[j])
                        if source_id_match:
                            source_id = source_id_match.group(1)
                            # Replace the through block
                            new_lines.append(lines[i])
                            new_lines.append('      source:')
                            new_lines.append('        space: fantasy_football')
                            new_lines.append(f'        externalId: {source_id}')
                            new_lines.append('        version: "1"')
                            new_lines.append('        type: view')
                            new_lines.append(lines[i+1])  # property line
                            i += 2
                            break
                else:
                    new_lines.append(line)
                    i += 1
            else:
                new_lines.append(line)
                i += 1
        else:
            new_lines.append(line)
            i += 1
    
    with open(filepath, 'w') as f:
        f.write('\n'.join(new_lines))
    
    print(f'Processed: {filepath}')

print('Done!')
