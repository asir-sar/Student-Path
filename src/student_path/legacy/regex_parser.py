"""LEGACY: the earlier pipe-table regex parser (formerly test.py at the project root).

Superseded; kept for reference (ADR-001). See student_path/legacy/__init__.py.
"""

import re
import json
import argparse
import sys

def parse_module_catalog(text):
    """
    Parses a markdown-like text representation of a module catalog 
    and normalizes it into a list of structured JSON dictionaries.
    """
    modules = []
    current_module = None
    
    # Buffers to hold multi-line keys and values
    pending_key = ""
    pending_val = ""

    # Helper function to flush the pending key/value pair into the module
    def flush_pending():
        nonlocal pending_key, pending_val, current_module
        if current_module is not None and pending_key:
            # Clean up extra spaces
            clean_key = re.sub(r'\s+', ' ', pending_key).strip()
            clean_val = re.sub(r'\s+', ' ', pending_val).strip()
            
            # If the key already exists (rare, but possible), append to it
            if clean_key in current_module:
                current_module[clean_key] += " \n " + clean_val
            else:
                current_module[clean_key] = clean_val
                
        pending_key = ""
        pending_val = ""

    # Split text into lines for sequential processing
    lines = text.split('\n')
    
    for line in lines:
        line = line.strip()
        
        # 1. Skip empty lines and pagination artifacts (headers/footers/page numbers)
        if not line or re.match(r'^\[Page \d+\]', line):
            continue
        if line in ["Modulkatalog", "Module Descriptions"] or re.match(r'^\d+$', line):
            continue
            
        # 2. Only process lines that belong to the table (start with '|')
        if not line.startswith('|'):
            continue

        # Split the row by the pipe character and clean whitespace
        parts = [p.strip() for p in line.split('|')]
        
        # A valid table row should have at least 3 parts: ['', 'Col1', 'Col2', ...]
        if len(parts) < 3:
            continue

        col1 = parts[1]
        col2 = parts[2]

        # Skip rows where both columns are completely empty (spacing rows)
        if not col1 and not col2:
            continue

        # Detect the start of a new module: Column 1 is a numeric ID (e.g., "5622")
        if re.match(r'^\d{3,}$', col1):
            flush_pending() # Flush any remaining data from the previous module
            
            # Save the previous module if it exists
            if current_module is not None:
                modules.append(current_module)
            
            # Initialize a new module object
            current_module = {
                "Module_ID": col1,
                "Module_Name": col2
            }
            continue

        # If we are currently inside a module, parse its attributes
        if current_module is not None:
            # Helper to append text with hyphenation awareness
            def append_text(current_text, new_text):
                if not new_text:
                    return current_text
                if not current_text:
                    return new_text
                
                # Check if the current text ends with a hyphen (ignoring trailing spaces)
                stripped_current = current_text.rstrip()
                if stripped_current.endswith('-'):
                    return stripped_current[:-1] + new_text
                else:
                    return current_text + " " + new_text

            # Logic to determine if this row starts a NEW property or continues the old one
            # It's a new property if col1 has text AND doesn't look like a continuation
            # A continuation usually starts with lowercase or follows a hyphenated key
            
            is_new_key = False
            if col1:
                if not pending_key:
                    is_new_key = True
                else:
                    # If pending key ends with hyphen, it's definitely a continuation
                    if pending_key.rstrip().endswith('-'):
                        is_new_key = False
                    # If col1 starts with lowercase, it's likely a continuation (e.g. "fungsordnung")
                    elif col1[0].islower():
                        is_new_key = False
                    # Otherwise, assume it's a new key/category
                    else:
                        is_new_key = True

            if is_new_key:
                # Flush the old one
                flush_pending()
                pending_key = col1
                pending_val = col2
            else:
                # Continue building the current key and value
                pending_key = append_text(pending_key, col1)
                pending_val = append_text(pending_val, col2)

    # Flush the very last key/value pair
    flush_pending()

    # Don't forget to append the very last module after the loop finishes
    if current_module is not None:
        modules.append(current_module)

    return modules

SAMPLE_TEXT = """
[Page 1]Modulkatalog
| 5622   | Software-Sicherheit  System Security  PN 405143   |
| Häufigkeit des Modulangebots  Frequency of course offering   | Jedes Sommersemester  Every summer semester   |
| Moduldauer  Module duration  Modulverantwortliche(r)  Module convenor  Dozent(in)  Lecturer  Sprache  Language of instruction   | 1 Semester  Posegga  Deutsch oder Englisch  German or English  Posegga   |
| 
| 
| Zuordnung zum Curriculum  Curriculum   | Modulgruppe  IT-SecRel"  Focus IT-SecRel"   |
| Lehrform/SWS  Contact hours   | $2V+1\dot{U}$   |
| Arbeitsaufwand  Workload   | 45 Std. Präsenz + 30 Std. Übungsaufgaben + 75 Std. Nach-  bearbeitung des Vorlesungsstoffes, Vorbereitung eines Refe-  rats und Prüfungsvorbereitung  45 contact hours + 30 hrs exercises + 75 hrs follow-up, pre-  paring a presentation and exam preparation   |
| ECTS  Credits   | 5   |
| Voraussetzungen nach Prü-   | Keine   |
| fungsordnung   | None   |
| Required prerequisites as per  the study and examination  regulations  Empfohlene Vorkenntnisse  Recommended skills  Verwendbarkeit in weiteren  Studiengängen  Applicability for other courses   | Advanced IT Security   |
| 
| Angestrebte Lernergebnisse  Learning outcomes   | Kenntnisse / Skills/Knowledge  Verständnis über Verwundbarkeiten deren Arten, Entstehung,   |
|  | Möglichkeiten der Ausnutzung und deren Folgen. Verstehen  der Prinzipien für die Entwicklung sicherer Software. Über-   |
Module Descriptions
48
[Page 2]Modulkatalog
Module Descriptions
|  | blick über Maßnahmen zur Schadensbegrenzung. Kenntnisse   |
|  | über Schritte zur forensischen Analyse von Sicherheitsvorfäl-  len. Überblick der Akademische Leitsätze und praxisrelevante,  ,,best practice" Ansätze.   |
|  | Understanding of the types of vulnerabilities, development,   |
|  | possibilities of use and its consequences. Understand the prin-   |
|  | ciples for the development of secure software. Overview of   |
|  | mitigation measures. Knowledge of steps for a forensic analy-   |
|  | sis of security incidents. Overview of Academic principles and  practice-relevant "best practice" approaches.  Fähigkeiten Abilities   |
|  | Aufspüren von Verwundbarkeiten; Ausbesserung von vorhan-  denen Verwundbarkeiten und forensische Analyse von Sicher-  heitsvorfällen.   |
|  | Detection of vulnerabilities; repair of existing vulnerabilities  and forensic analysis of security incidents.  Kompetenzen / Competencies  Betrachtung von Systemen aus unterschiedlichen Blickwin-  keln. Entwicklung, Analyse und Umsetzung möglicher Per-  spektiven und Reaktionsalternativen. Transformation und Re-  duktion akademischer Leitsätze auf praxisbezogene Anforde-  rungen.   |
|  | Consideration of systems from different angles. Development,  analysis and implementation of possible perspectives and re-  sponse alternatives. Transformation and reduction of acade-  mic principles to practical requirements.   |
| Inhalt  Course content   | Der Inhalt des Moduls umfasst dabei z.B. risk & threat analy-  sis, buffer und heap overflows, scripting languages, filter tech-  niques, SQL injections, race conditions, attack surfaces, patch  management, software testing, low level software security, Ja-   |
|  | va security, reference monitors, least privilege principle, smart   |
|  | phone security, stack walks und history based access control.   |
|  | The content of the module includes, i.e., risk & threat analysis,  buffer and heap overflows, scripting languages, filter techni-  ques, SQL injections, race conditions, attack surfaces, patch  management, software testing, low-level software security, Ja-  va security, reference monitors, leases privilege principle, smart  phone security, stack walks and history based access control.   |
| 
| Studien-/Prüfungsleistungen  Assessment   | Teilprüfungsleistungen:  • Referat: ca. 30-min. Referat mit Präsentation über   |
49
[Page 3]Modulkatalog
Module Descriptions
|  | selbsterarbeitetes Thema. Die Studierenden können am   |
|  | Semesterbeginn aus einer Auswahl von Themen wählen.   |
|  | • Schriftliche/mündliche Prüfung: 60-min. schriftliche  Prüfung oder ca. 20-min. mündliche Prüfung. Die Prü-   |
|  | fungsart wird am Semesterbeginn durch den/die Do-   |
|  | zent(in) festgelegt und bekanntgegeben.   |
|  | Eine Anmeldung zum Referat impliziert automatisch eine An-   |
|  | meldung zu einem der angebotenen Termine zur schriftli-   |
|  | chen/mündlichen Prüfung im Anschluss an den gleichen Vor-   |
|  | lesungszeitraum.   |
|  | Zum Bestehen des Moduls müssen beide Teilprüfungsleistun-   |
|  | gen bestanden werden. Dabei wird die schriftliche/mündliche   |
|  | Prüfung mit 80% gewichtet, das Referat mit 20%.   |
|  | This module is assessed in partial examinations:   |
|  | • Oral presentation: approx 20 min. Students in small   |
|  | groups will present selected topics chosen during the  semester.   |
|  | • 60-minute written or 20-minute oral examination. The   |
|  | specific mode of assessment will be announced by the   |
|  | lecturer at the start of the semester.   |
|  | Registration for the presentation automatically implies a re-   |
|  |
|  | gistration for any of the dates offered for written/oral exami-  nation following the same course of lectures.  In order to pass this module, students must pass both partial  examinations. The exam will count 80% of the grade, the oral  presentation 20%.   |
| Medienformen  Media used   | Präsentation und Beamer, Tafel  Presentation and projector, blackboard   |
| Literatur   | Michael Howard & David LeBlanc: Writing Secure Code, Mi-   |
| Reading list   | crosoft Press, 2nd edition, 2002  Gary McGraw: Exploiting Software: How to Break Code,   |
|  | Addison-Wesley, February 2004  John Viega & Gary McGraw: Building Secure Software,  Addison-Wesley, 2001  Mark G. Graff & Kenneth R. van Wyk: Secure Coding,   |
|  | O.Reilly, 2003   |
|  | Brian A. La Macchia, Sebastian Lange, Matthew Lyons, Ru-   |
|  | Security,  di Martin, and Kevin T. Price: .NET Framework  Addison-Wesley, 2002  L. Gong, G. Ellison, M. Dageforde: Inside Java 2 Platform  Security, Addison-Wesley, 2nd Edition, 2003   |
50
"""

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Normalize University PDF Table extractions to JSON.")
    parser.add_argument("-i", "--input", help="Path to the input text file (extracted from PDF). If omitted, runs the built-in sample.")
    parser.add_argument("-o", "--output", help="Path to save the output JSON file. Defaults to stdout.")
    
    # Use parse_known_args instead of parse_args to ignore injected sandbox arguments like --rpc_input
    args, unknown = parser.parse_known_args()
    
    # Read text from file or use sample
    if args.input:
        try:
            with open(args.input, 'r', encoding='utf-8') as f:
                text_data = f.read()
        except Exception as e:
            print(f"Error reading input file: {e}")
            sys.exit(1)
    else:
        print("No input file provided. Running with the embedded sample data...\n")
        text_data = SAMPLE_TEXT
        
    # Run the normalizer
    extracted_modules = parse_module_catalog(text_data)
    
    # Output formatting
    json_output = json.dumps(extracted_modules, indent=4, ensure_ascii=False)
    
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(json_output)
        print(f"Successfully saved {len(extracted_modules)} modules to {args.output}")
    else:
        print(json_output)