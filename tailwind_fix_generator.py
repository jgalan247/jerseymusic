"""
Tailwind Analysis to Fix Commands Generator
Converts consistency analysis results into actionable Claude commands
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict
import re

class TailwindFixGenerator:
    def __init__(self, report_file='tailwind_consistency_report.json'):
        """Initialize with the analysis report."""
        self.report_file = report_file
        self.fixes = []
        self.component_templates = {}
        self.files_to_update = defaultdict(list)
        
    def load_report(self):
        """Load the analysis report."""
        try:
            with open(self.report_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"❌ Report file {self.report_file} not found")
            return None
    
    def analyze_inconsistencies(self, report):
        """Parse the report and identify specific fixes needed."""
        inconsistencies = report.get('inconsistencies', [])
        detailed_results = report.get('detailed_results', {})
        
        fixes_by_category = defaultdict(list)
        
        for issue in inconsistencies:
            category = issue['category']
            problem = issue['issue']
            fixes_by_category[category].append(problem)
        
        return fixes_by_category, detailed_results
    
    def generate_standardized_classes(self, detailed_results):
        """Generate standardized Tailwind classes based on analysis."""
        standards = {
            'h1': 'text-4xl md:text-5xl font-bold text-gray-900',
            'h2': 'text-3xl md:text-4xl font-semibold text-gray-900',
            'h3': 'text-2xl md:text-3xl font-semibold text-gray-800',
            'h4': 'text-xl md:text-2xl font-medium text-gray-800',
            'p': 'text-base text-gray-700 leading-relaxed',
            'button_primary': 'px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-md transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2',
            'button_secondary': 'px-5 py-2.5 bg-gray-200 hover:bg-gray-300 text-gray-800 font-medium rounded-md transition-colors duration-150',
            'container': 'max-w-7xl mx-auto px-4 sm:px-6 lg:px-8',
            'section': 'py-12 md:py-16 lg:py-20',
            'card': 'bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow duration-200 p-6',
            'form_input': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
        }
        
        # Analyze actual usage from results to refine standards
        if 'headers' in detailed_results:
            headers = detailed_results['headers']
            # Count most common patterns for each tag
            tag_patterns = defaultdict(list)
            for header in headers:
                tag = header['tag']
                classes = header['all_classes']
                if classes:
                    tag_patterns[tag].append(classes)
            
            # You could analyze these patterns to adjust standards
            # For now, we'll use the predefined standards
        
        return standards
    
    def generate_fix_commands(self, fixes_by_category, standards):
        """Generate specific Claude commands for each fix."""
        commands = []
        
        # Group fixes by type
        typography_fixes = [f for cat, f in fixes_by_category.items() if 'Typography' in cat or 'Heading' in cat]
        button_fixes = [f for cat, f in fixes_by_category.items() if 'Button' in cat]
        container_fixes = [f for cat, f in fixes_by_category.items() if 'Container' in cat]
        spacing_fixes = [f for cat, f in fixes_by_category.items() if 'Spacing' in cat]
        
        # Generate commands for each type
        if typography_fixes:
            commands.append(self._generate_typography_fix_command(standards))
        
        if button_fixes:
            commands.append(self._generate_button_fix_command(standards))
        
        if container_fixes:
            commands.append(self._generate_container_fix_command(standards))
        
        if spacing_fixes:
            commands.append(self._generate_spacing_fix_command(standards))
        
        return commands
    
    def _generate_typography_fix_command(self, standards):
        """Generate typography fix command."""
        return {
            'type': 'typography',
            'command': f"""
Fix all typography inconsistencies in Django templates:

1. Find and replace ALL heading tags with standardized Tailwind classes:
   - <h1> tags: class="{standards['h1']}"
   - <h2> tags: class="{standards['h2']}"
   - <h3> tags: class="{standards['h3']}"
   - <h4> tags: class="{standards['h4']}"
   - <p> tags for body text: class="{standards['p']}"

2. Search for these patterns and replace:
   - Any h1 with class="text-3xl" → class="{standards['h1']}"
   - Any h2 with class="text-2xl" → class="{standards['h2']}"
   - Inconsistent font-weight classes → Use the standards above

3. Files to check and update:
   - templates/events/home.html
   - templates/events/events_list.html
   - templates/events/event_detail.html
   - templates/accounts/login.html
   - templates/accounts/register.html
""",
            'files_pattern': 'templates/**/*.html'
        }
    
    def _generate_button_fix_command(self, standards):
        """Generate button fix command."""
        return {
            'type': 'buttons',
            'command': f"""
Standardize all buttons across the application:

1. Create a new template component:
   File: templates/components/button.html
   ```django
   {{% load widget_tweaks %}}
   {{% if variant == 'primary' %}}
     <button class="{standards['button_primary']}" {{{{ attrs }}}}>
       {{{{ text }}}}
     </button>
   {{% elif variant == 'secondary' %}}
     <button class="{standards['button_secondary']}" {{{{ attrs }}}}>
       {{{{ text }}}}
     </button>
   {{% endif %}}
   ```

2. Replace all existing buttons:
   - Find: <button class="px-4 py-2 bg-blue-500...">
   - Replace with: {{% include 'components/button.html' with variant='primary' text='Button Text' %}}
   
3. Update form submit buttons:
   - Find: <input type="submit" class="...">
   - Replace with: <button type="submit" class="{standards['button_primary']}">Submit</button>

4. Files to update:
   - All templates with buttons or CTAs
   - Special attention to: events/create_event.html, accounts/login.html
""",
            'files_pattern': 'templates/**/*.html'
        }
    
    def _generate_container_fix_command(self, standards):
        """Generate container fix command."""
        return {
            'type': 'containers',
            'command': f"""
Fix all container widths and layouts:

1. Standardize main containers:
   - Replace all variations of max-w-* on main containers
   - Use: class="{standards['container']}"

2. Create base template structure:
   File: templates/base.html
   ```django
   <body class="bg-gray-50">
     <nav class="bg-white shadow-sm">
       <div class="{standards['container']}">
         {{% block navigation %}}...{{% endblock %}}
       </div>
     </nav>
     
     <main class="min-h-screen">
       <div class="{standards['container']} {standards['section']}">
         {{% block content %}}...{{% endblock %}}
       </div>
     </main>
     
     <footer class="bg-gray-900 text-white">
       <div class="{standards['container']} py-8">
         {{% block footer %}}...{{% endblock %}}
       </div>
     </footer>
   </body>
   ```

3. Update all templates extending base.html:
   - Remove redundant container divs
   - Ensure consistent spacing
""",
            'files_pattern': 'templates/base.html'
        }
    
    def _generate_spacing_fix_command(self, standards):
        """Generate spacing fix command."""
        return {
            'type': 'spacing',
            'command': f"""
Standardize spacing across all components:

1. Section spacing:
   - All main sections: class="... {standards['section']}"
   - Remove custom py-* classes that vary

2. Card spacing:
   - All cards: class="{standards['card']}"
   - Content within cards: consistent p-6

3. Form spacing:
   - Form groups: class="space-y-4"
   - Form inputs: class="{standards['form_input']}"
   
4. List spacing:
   - Event lists: class="grid gap-6 md:grid-cols-2 lg:grid-cols-3"
   - Menu items: class="space-y-2"

5. Global spacing rules:
   - Use multiples of 4 (Tailwind default): 4, 8, 12, 16, 20, 24
   - Mobile: smaller values (p-4, py-8)
   - Desktop: larger values (p-6, py-12)
""",
            'files_pattern': 'templates/**/*.html'
        }
    
    def generate_claude_prompt(self, commands):
        """Generate a comprehensive Claude prompt."""
        prompt = """
# Tailwind CSS Consistency Fixes for Jersey Events Django App

I need you to help fix Tailwind CSS inconsistencies across my Django templates. 
The analysis found several issues that need to be standardized.

## Standard Classes to Use Everywhere:

```python
STANDARD_CLASSES = {
    'h1': 'text-4xl md:text-5xl font-bold text-gray-900',
    'h2': 'text-3xl md:text-4xl font-semibold text-gray-900',
    'h3': 'text-2xl md:text-3xl font-semibold text-gray-800',
    'h4': 'text-xl md:text-2xl font-medium text-gray-800',
    'p': 'text-base text-gray-700 leading-relaxed',
    'button_primary': 'px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-md transition-colors duration-150',
    'button_secondary': 'px-5 py-2.5 bg-gray-200 hover:bg-gray-300 text-gray-800 font-medium rounded-md',
    'container': 'max-w-7xl mx-auto px-4 sm:px-6 lg:px-8',
    'section': 'py-12 md:py-16 lg:py-20',
    'card': 'bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow duration-200 p-6',
}
```

## Specific Fixes Required:

"""
        for i, cmd in enumerate(commands, 1):
            prompt += f"\n### Fix {i}: {cmd['type'].upper()}\n"
            prompt += cmd['command']
            prompt += "\n"
        
        prompt += """

## Implementation Steps:

1. Start with the base template to ensure consistent structure
2. Create the component templates in templates/components/
3. Update each page template to use the standardized classes
4. Test each page to ensure consistency

## Files Priority Order:

1. templates/base.html (foundation)
2. templates/components/*.html (reusable components)
3. templates/events/*.html (main app templates)
4. templates/accounts/*.html (auth templates)

Please provide the updated template files with these fixes applied.
"""
        return prompt
    
    def generate_component_library(self, standards):
        """Generate a complete component library."""
        components = {}
        
        # Button component
        components['button.html'] = f"""
{{% comment %}}
Button Component
Usage: {{% include 'components/button.html' with variant='primary' text='Click Me' size='md' %}}
Variants: primary, secondary, outline, danger
Sizes: sm, md, lg
{{% endcomment %}}

{{% load widget_tweaks %}}

{{% if size == 'sm' %}}
  {{% with size_classes='px-3 py-1.5 text-sm' %}}
{{% elif size == 'lg' %}}
  {{% with size_classes='px-6 py-3 text-lg' %}}
{{% else %}}
  {{% with size_classes='px-5 py-2.5 text-base' %}}
{{% endif %}}

{{% if variant == 'primary' %}}
  <button class="{{{{ size_classes }}}} bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-md transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 {{{{ extra_classes }}}}" {{{{ attrs|safe }}}}>
    {{{{ text }}}}
  </button>
{{% elif variant == 'secondary' %}}
  <button class="{{{{ size_classes }}}} bg-gray-200 hover:bg-gray-300 text-gray-800 font-medium rounded-md transition-colors duration-150 {{{{ extra_classes }}}}" {{{{ attrs|safe }}}}>
    {{{{ text }}}}
  </button>
{{% elif variant == 'outline' %}}
  <button class="{{{{ size_classes }}}} border-2 border-blue-600 text-blue-600 hover:bg-blue-600 hover:text-white font-medium rounded-md transition-colors duration-150 {{{{ extra_classes }}}}" {{{{ attrs|safe }}}}>
    {{{{ text }}}}
  </button>
{{% elif variant == 'danger' %}}
  <button class="{{{{ size_classes }}}} bg-red-600 hover:bg-red-700 text-white font-medium rounded-md transition-colors duration-150 {{{{ extra_classes }}}}" {{{{ attrs|safe }}}}>
    {{{{ text }}}}
  </button>
{{% endif %}}

{{% endwith %}}
"""
        
        # Card component
        components['card.html'] = f"""
{{% comment %}}
Card Component
Usage: {{% include 'components/card.html' with title='Event Title' description='Event description' image_url='/media/event.jpg' %}}
{{% endcomment %}}

<div class="{standards['card']} overflow-hidden">
  {{% if image_url %}}
    <img src="{{{{ image_url }}}}" alt="{{{{ title }}}}" class="w-full h-48 object-cover -m-6 mb-4">
  {{% endif %}}
  
  {{% if title %}}
    <h3 class="text-xl font-semibold text-gray-900 mb-2">{{{{ title }}}}</h3>
  {{% endif %}}
  
  {{% if description %}}
    <p class="text-gray-600 mb-4">{{{{ description }}}}</p>
  {{% endif %}}
  
  {{% if cta_text %}}
    <div class="mt-4">
      {{% include 'components/button.html' with variant=cta_variant|default:'primary' text=cta_text %}}
    </div>
  {{% endif %}}
  
  {{% block card_content %}}
  {{% endblock %}}
</div>
"""
        
        # Form input component
        components['form_input.html'] = f"""
{{% comment %}}
Form Input Component
Usage: {{% include 'components/form_input.html' with field=form.email label='Email Address' %}}
{{% endcomment %}}

{{% load widget_tweaks %}}

<div class="mb-4">
  {{% if label %}}
    <label for="{{{{ field.id_for_label }}}}" class="block text-sm font-medium text-gray-700 mb-1">
      {{{{ label }}}}
      {{% if field.field.required %}}
        <span class="text-red-500">*</span>
      {{% endif %}}
    </label>
  {{% endif %}}
  
  {{% render_field field class="{standards['form_input']}" %}}
  
  {{% if field.errors %}}
    <p class="mt-1 text-sm text-red-600">
      {{{{ field.errors|first }}}}
    </p>
  {{% endif %}}
  
  {{% if field.help_text %}}
    <p class="mt-1 text-sm text-gray-500">
      {{{{ field.help_text }}}}
    </p>
  {{% endif %}}
</div>
"""
        
        return components
    
    def save_fixes(self, commands, prompt, components):
        """Save all fixes to files."""
        output_dir = Path('tailwind_fixes')
        output_dir.mkdir(exist_ok=True)
        
        # Save Claude prompt
        with open(output_dir / 'claude_prompt.md', 'w') as f:
            f.write(prompt)
        
        # Save individual fix commands
        for i, cmd in enumerate(commands, 1):
            with open(output_dir / f'fix_{i}_{cmd["type"]}.md', 'w') as f:
                f.write(f"# Fix {i}: {cmd['type'].upper()}\n\n")
                f.write(cmd['command'])
        
        # Save component templates
        components_dir = output_dir / 'components'
        components_dir.mkdir(exist_ok=True)
        
        for filename, content in components.items():
            with open(components_dir / filename, 'w') as f:
                f.write(content)
        
        # Save a shell script to apply fixes
        with open(output_dir / 'apply_fixes.sh', 'w') as f:
            f.write("""#!/bin/bash
# Script to apply Tailwind fixes to your Django project

echo "Creating components directory..."
mkdir -p templates/components

echo "Copying component templates..."
cp components/*.html templates/components/

echo "Component templates installed!"
echo "Now update your templates according to the fix commands."
echo "Use 'cat claude_prompt.md' to see the full instructions for Claude."
""")
        
        print(f"\n✅ Fixes saved to {output_dir}/")
        print(f"   - claude_prompt.md: Complete prompt for Claude")
        print(f"   - components/: Ready-to-use component templates")
        print(f"   - apply_fixes.sh: Script to install components")
    
    def run(self):
        """Main execution method."""
        print("🔄 Loading Tailwind consistency report...")
        report = self.load_report()
        
        if not report:
            return
        
        print("📊 Analyzing inconsistencies...")
        fixes_by_category, detailed_results = self.analyze_inconsistencies(report)
        
        print(f"   Found {len(fixes_by_category)} categories with issues")
        
        print("🎯 Generating standardized classes...")
        standards = self.generate_standardized_classes(detailed_results)
        
        print("📝 Creating fix commands...")
        commands = self.generate_fix_commands(fixes_by_category, standards)
        
        print("🤖 Generating Claude prompt...")
        prompt = self.generate_claude_prompt(commands)
        
        print("🧩 Creating component library...")
        components = self.generate_component_library(standards)
        
        print("💾 Saving fixes...")
        self.save_fixes(commands, prompt, components)
        
        print("\n" + "="*60)
        print("✨ FIX GENERATION COMPLETE!")
        print("="*60)
        print("""
Next steps:
1. Review the generated fixes in 'tailwind_fixes/' directory
2. Copy the Claude prompt from 'tailwind_fixes/claude_prompt.md'
3. Paste it to Claude to get updated template files
4. Or manually apply the fixes using the component templates

Quick command to get the Claude prompt:
$ cat tailwind_fixes/claude_prompt.md | pbcopy  # Mac
$ cat tailwind_fixes/claude_prompt.md | xclip  # Linux

The prompt includes:
- Specific search-and-replace patterns
- Component templates to create
- Files to update
- Standard classes to use consistently
""")
        
        return prompt, commands, components


# Additional utility to find and fix specific files
class TemplateFixApplier:
    """Applies fixes directly to Django template files."""
    
    def __init__(self, project_path='.'):
        self.project_path = Path(project_path)
        self.templates_path = self.project_path / 'templates'
        
    def find_templates(self):
        """Find all HTML templates in the project."""
        return list(self.templates_path.rglob('*.html'))
    
    def fix_typography_in_file(self, filepath, standards):
        """Fix typography classes in a single file."""
        with open(filepath, 'r') as f:
            content = f.read()
        
        # Pattern replacements
        replacements = [
            (r'<h1[^>]*class="[^"]*"', f'<h1 class="{standards["h1"]}"'),
            (r'<h2[^>]*class="[^"]*"', f'<h2 class="{standards["h2"]}"'),
            (r'<h3[^>]*class="[^"]*"', f'<h3 class="{standards["h3"]}"'),
            (r'<h4[^>]*class="[^"]*"', f'<h4 class="{standards["h4"]}"'),
        ]
        
        original = content
        for pattern, replacement in replacements:
            content = re.sub(pattern, replacement, content)
        
        if content != original:
            # Create backup
            backup_path = filepath.with_suffix('.html.bak')
            with open(backup_path, 'w') as f:
                f.write(original)
            
            # Write fixed content
            with open(filepath, 'w') as f:
                f.write(content)
            
            return True
        return False
    
    def apply_fixes_to_project(self, standards):
        """Apply fixes to all template files."""
        templates = self.find_templates()
        fixed_files = []
        
        for template in templates:
            if self.fix_typography_in_file(template, standards):
                fixed_files.append(template)
        
        print(f"\n📝 Fixed {len(fixed_files)} template files")
        for f in fixed_files:
            print(f"   ✓ {f.relative_to(self.project_path)}")


def main():
    """Main execution function."""
    # Generate fix commands from the report
    generator = TailwindFixGenerator('tailwind_consistency_report.json')
    prompt, commands, components = generator.run()
    
    # Optionally, directly apply some fixes
    # applier = TemplateFixApplier('.')
    # applier.apply_fixes_to_project(generator.generate_standardized_classes({}))


if __name__ == "__main__":
    main()