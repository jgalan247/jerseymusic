"""
Tailwind CSS Consistency Checker for Django Jersey Events
Analyzes Tailwind utility class usage across your Django application pages.
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
from collections import defaultdict, Counter
import time
from typing import Dict, List, Set, Tuple
import re

class TailwindConsistencyChecker:
    def __init__(self, base_url='http://localhost:8000', headless=True):
        """
        Initialize the web driver for Tailwind consistency checking.
        
        Args:
            base_url: Your Django development server URL
            headless: Run browser in headless mode
        """
        self.base_url = base_url.rstrip('/')
        
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.results = defaultdict(list)
        self.class_usage = defaultdict(Counter)
        self.component_patterns = defaultdict(set)
        self.inconsistencies = []
        
    def get_django_urls(self):
        """Return URLs based on your Django URL configuration."""
        urls = {
            # Events app URLs
            'home': f"{self.base_url}/",
            'events_list': f"{self.base_url}/events/",
            'about': f"{self.base_url}/about/",
            'contact': f"{self.base_url}/contact/",
            'organisers': f"{self.base_url}/organisers/",
            
            # Account URLs
            'login': f"{self.base_url}/accounts/login/",
            'register_customer': f"{self.base_url}/accounts/register/customer/",
            'register_organiser': f"{self.base_url}/accounts/register/organiser/",
            'profile': f"{self.base_url}/accounts/profile/",
            
            # Legal pages
            'privacy': f"{self.base_url}/privacy/",
            'terms': f"{self.base_url}/terms/",
            'refund': f"{self.base_url}/refund-policy/",
        }
        return urls
    
    def extract_tailwind_classes(self, element):
        """Extract and categorize Tailwind classes from an element."""
        class_string = element.get_attribute('class') or ''
        if not class_string:
            return {}
        
        classes = class_string.split()
        
        # Categorize Tailwind classes
        categorized = {
            'spacing': [],      # p-, m-, space-
            'typography': [],   # text-, font-, leading-
            'layout': [],       # flex, grid, container, max-w-
            'sizing': [],       # w-, h-, min-, max-
            'background': [],   # bg-
            'border': [],       # border-, rounded-
            'effects': [],      # shadow-, opacity-
            'responsive': [],   # sm:, md:, lg:, xl:
            'state': [],        # hover:, focus:, active:
            'other': []
        }
        
        for cls in classes:
            if cls.startswith(('p-', 'px-', 'py-', 'pt-', 'pr-', 'pb-', 'pl-',
                             'm-', 'mx-', 'my-', 'mt-', 'mr-', 'mb-', 'ml-',
                             'space-', 'gap-')):
                categorized['spacing'].append(cls)
            elif cls.startswith(('text-', 'font-', 'leading-', 'tracking-')):
                categorized['typography'].append(cls)
            elif cls.startswith(('flex', 'grid', 'container', 'max-w-', 'min-w-')):
                categorized['layout'].append(cls)
            elif cls.startswith(('w-', 'h-', 'min-h-', 'max-h-', 'min-w-', 'max-w-')):
                categorized['sizing'].append(cls)
            elif cls.startswith('bg-'):
                categorized['background'].append(cls)
            elif cls.startswith(('border', 'rounded')):
                categorized['border'].append(cls)
            elif cls.startswith(('shadow', 'opacity')):
                categorized['effects'].append(cls)
            elif ':' in cls and cls.split(':')[0] in ['sm', 'md', 'lg', 'xl', '2xl']:
                categorized['responsive'].append(cls)
            elif ':' in cls and cls.split(':')[0] in ['hover', 'focus', 'active', 'disabled']:
                categorized['state'].append(cls)
            else:
                categorized['other'].append(cls)
        
        return categorized
    
    def analyze_element(self, element, element_type=""):
        """Analyze Tailwind classes and computed styles of an element."""
        try:
            # Get Tailwind classes
            tailwind_classes = self.extract_tailwind_classes(element)
            
            # Get computed styles for verification
            computed_styles = self.driver.execute_script("""
                var elem = arguments[0];
                var styles = window.getComputedStyle(elem);
                return {
                    'fontSize': styles.fontSize,
                    'fontWeight': styles.fontWeight,
                    'padding': styles.padding,
                    'margin': styles.margin,
                    'backgroundColor': styles.backgroundColor,
                    'borderRadius': styles.borderRadius,
                    'maxWidth': styles.maxWidth
                };
            """, element)
            
            # Get element details
            tag_name = element.tag_name
            all_classes = element.get_attribute('class') or ''
            text_preview = element.text[:50] if element.text else ''
            
            return {
                'tag': tag_name,
                'all_classes': all_classes,
                'tailwind_classes': tailwind_classes,
                'computed_styles': computed_styles,
                'text_preview': text_preview,
                'element_type': element_type
            }
        except Exception as e:
            return None
    
    def check_page(self, url: str, page_name: str):
        """Analyze a single page for Tailwind class consistency."""
        print(f"\n📄 Analyzing: {page_name}")
        print(f"   URL: {url}")
        
        try:
            self.driver.get(url)
            time.sleep(2)
            
            # Check if login is required
            current_url = self.driver.current_url
            if '/login/' in current_url and '/login/' not in url:
                print(f"   ⚠️ Page requires authentication, skipping...")
                return
            
            # Wait for body to be present
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Component patterns to check
            component_selectors = {
                'headers': 'h1, h2, h3, h4',
                'buttons': 'button, a.btn, [class*="btn"], input[type="submit"]',
                'cards': '[class*="card"], [class*="event-card"]',
                'containers': '.container, main, section, [class*="max-w-"]',
                'forms': 'form, input, textarea, select',
                'navigation': 'nav, header, [class*="navbar"]',
                'links': 'a:not([class*="btn"])'
            }
            
            for component_type, selector in component_selectors.items():
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in elements[:5]:  # Sample first 5
                        if elem.is_displayed():
                            data = self.analyze_element(elem, component_type)
                            if data:
                                data['page'] = page_name
                                data['url'] = url
                                self.results[component_type].append(data)
                                
                                # Track class usage patterns
                                for category, classes in data['tailwind_classes'].items():
                                    if classes:
                                        class_pattern = ' '.join(sorted(classes))
                                        self.component_patterns[f"{component_type}_{category}"].add(
                                            (page_name, class_pattern)
                                        )
                                        
                                        # Count individual class usage
                                        for cls in classes:
                                            self.class_usage[component_type][cls] += 1
                except Exception as e:
                    pass
                    
        except Exception as e:
            print(f"   ❌ Error analyzing page: {e}")
    
    def find_tailwind_inconsistencies(self):
        """Identify Tailwind utility class inconsistencies."""
        print("\n" + "="*60)
        print("🎨 TAILWIND CSS CONSISTENCY ANALYSIS")
        print("="*60)
        
        issues = []
        
        # Check heading consistency
        print("\n📝 Typography Classes Analysis:")
        self._check_typography_consistency(issues)
        
        # Check button consistency
        print("\n🔘 Button Classes Analysis:")
        self._check_button_consistency(issues)
        
        # Check spacing consistency
        print("\n📐 Spacing Classes Analysis:")
        self._check_spacing_consistency(issues)
        
        # Check container consistency
        print("\n📦 Container Classes Analysis:")
        self._check_container_consistency(issues)
        
        self.inconsistencies = issues
        return issues
    
    def _check_typography_consistency(self, issues):
        """Check typography Tailwind classes consistency."""
        if 'headers' in self.results:
            headers = self.results['headers']
            
            # Group by tag name
            tag_patterns = defaultdict(set)
            for header in headers:
                tag = header['tag']
                typography_classes = ' '.join(sorted(header['tailwind_classes']['typography']))
                tag_patterns[tag].add((header['page'], typography_classes))
            
            # Report inconsistencies
            for tag, patterns in tag_patterns.items():
                unique_patterns = set(p[1] for p in patterns)
                if len(unique_patterns) > 1:
                    issue = f"{tag.upper()} uses {len(unique_patterns)} different typography patterns"
                    issues.append((f'{tag.upper()} Typography', issue))
                    print(f"   ⚠️ {issue}:")
                    
                    for page, pattern in patterns:
                        if pattern:
                            print(f"      • {page}: {pattern}")
                        else:
                            print(f"      • {page}: [no typography classes]")
    
    def _check_button_consistency(self, issues):
        """Check button Tailwind classes consistency."""
        if 'buttons' in self.results:
            buttons = self.results['buttons']
            
            # Collect all button class combinations
            button_patterns = defaultdict(list)
            for button in buttons:
                # Combine relevant categories for buttons
                pattern_key = {
                    'spacing': ' '.join(sorted(button['tailwind_classes']['spacing'])),
                    'typography': ' '.join(sorted(button['tailwind_classes']['typography'])),
                    'background': ' '.join(sorted(button['tailwind_classes']['background'])),
                    'border': ' '.join(sorted(button['tailwind_classes']['border'])),
                }
                
                pattern_str = json.dumps(pattern_key, sort_keys=True)
                button_patterns[pattern_str].append(button['page'])
            
            if len(button_patterns) > 3:  # Allow primary, secondary, tertiary
                issue = f"Found {len(button_patterns)} different button patterns (expected max 3)"
                issues.append(('Button Patterns', issue))
                print(f"   ⚠️ {issue}")
                
                for pattern_str, pages in button_patterns.items():
                    pattern = json.loads(pattern_str)
                    print(f"      • Pattern on {', '.join(set(pages))}:")
                    for key, value in pattern.items():
                        if value:
                            print(f"        - {key}: {value}")
    
    def _check_spacing_consistency(self, issues):
        """Check spacing Tailwind classes consistency."""
        # Analyze spacing patterns across similar components
        spacing_patterns = defaultdict(lambda: defaultdict(set))
        
        for component_type, elements in self.results.items():
            for elem in elements:
                spacing_classes = elem['tailwind_classes']['spacing']
                if spacing_classes:
                    pattern = ' '.join(sorted(spacing_classes))
                    spacing_patterns[component_type][pattern].add(elem['page'])
        
        for component_type, patterns in spacing_patterns.items():
            if len(patterns) > 2:  # Some variation is acceptable
                issue = f"{component_type} has {len(patterns)} different spacing patterns"
                issues.append((f'{component_type} Spacing', issue))
                print(f"   ⚠️ {issue}")
    
    def _check_container_consistency(self, issues):
        """Check container Tailwind classes consistency."""
        if 'containers' in self.results:
            containers = self.results['containers']
            
            # Check max-width classes
            max_widths = defaultdict(list)
            for container in containers:
                layout_classes = container['tailwind_classes']['layout']
                max_w_class = next((c for c in layout_classes if c.startswith('max-w-')), 'none')
                max_widths[max_w_class].append(container['page'])
            
            if len(max_widths) > 2:  # Some pages might have different layouts
                issue = f"Found {len(max_widths)} different max-width values"
                issues.append(('Container Width', issue))
                print(f"   ⚠️ {issue}:")
                for max_w, pages in max_widths.items():
                    print(f"      • {max_w}: {', '.join(set(pages))}")
    
    def generate_tailwind_config_suggestions(self):
        """Generate tailwind.config.js suggestions for consistency."""
        print("\n" + "="*60)
        print("⚙️ TAILWIND CONFIGURATION SUGGESTIONS")
        print("="*60)
        
        print("""
// tailwind.config.js
module.exports = {
  content: [
    './templates/**/*.html',
    './static/js/**/*.js',
  ],
  theme: {
    extend: {
      // Define custom spacing scale for consistency
      spacing: {
        'xs': '0.5rem',   // 8px
        'sm': '1rem',     // 16px
        'md': '1.5rem',   // 24px
        'lg': '2rem',     // 32px
        'xl': '3rem',     // 48px
        '2xl': '4rem',    // 64px
      },
      
      // Consistent max-widths for containers
      maxWidth: {
        'container': '1200px',
        'content': '800px',
        'narrow': '600px',
      },
      
      // Typography scale
      fontSize: {
        'h1': ['2.5rem', { lineHeight: '1.2', fontWeight: '700' }],
        'h2': ['2rem', { lineHeight: '1.2', fontWeight: '600' }],
        'h3': ['1.75rem', { lineHeight: '1.3', fontWeight: '600' }],
        'h4': ['1.5rem', { lineHeight: '1.4', fontWeight: '500' }],
      },
      
      // Brand colors
      colors: {
        'primary': '#0066ff',
        'primary-hover': '#0052cc',
        'secondary': '#6c757d',
      },
    },
  },
  plugins: [],
}
""")
    
    def generate_component_classes(self):
        """Generate reusable Tailwind component classes."""
        print("\n" + "="*60)
        print("🧩 RECOMMENDED TAILWIND COMPONENT CLASSES")
        print("="*60)
        
        print("""
<!-- Create reusable Django template components -->

<!-- templates/components/button.html -->
{% comment %}
Usage: {% include 'components/button.html' with variant='primary' text='Click me' %}
{% endcomment %}

{% if variant == 'primary' %}
  <button class="px-5 py-2.5 bg-primary hover:bg-primary-hover text-white font-medium 
                 rounded-md transition-colors duration-150 focus:outline-none 
                 focus:ring-2 focus:ring-primary focus:ring-offset-2">
    {{ text }}
  </button>
  
{% elif variant == 'secondary' %}
  <button class="px-5 py-2.5 bg-gray-200 hover:bg-gray-300 text-gray-800 font-medium 
                 rounded-md transition-colors duration-150 focus:outline-none 
                 focus:ring-2 focus:ring-gray-500 focus:ring-offset-2">
    {{ text }}
  </button>
  
{% elif variant == 'outline' %}
  <button class="px-5 py-2.5 border border-primary text-primary hover:bg-primary 
                 hover:text-white font-medium rounded-md transition-colors duration-150 
                 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2">
    {{ text }}
  </button>
{% endif %}

<!-- templates/components/heading.html -->
{% if level == 1 %}
  <h1 class="text-4xl md:text-5xl font-bold text-gray-900 mb-4">{{ text }}</h1>
{% elif level == 2 %}
  <h2 class="text-3xl md:text-4xl font-semibold text-gray-900 mb-3">{{ text }}</h2>
{% elif level == 3 %}
  <h3 class="text-2xl md:text-3xl font-semibold text-gray-800 mb-2">{{ text }}</h3>
{% endif %}

<!-- templates/components/container.html -->
<div class="max-w-container mx-auto px-4 sm:px-6 lg:px-8">
  {{ content|safe }}
</div>

<!-- templates/components/card.html -->
<div class="bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow 
            duration-200 overflow-hidden">
  {% if image %}
    <img src="{{ image }}" alt="{{ title }}" class="w-full h-48 object-cover">
  {% endif %}
  <div class="p-6">
    <h3 class="text-xl font-semibold text-gray-900 mb-2">{{ title }}</h3>
    <p class="text-gray-600 mb-4">{{ description }}</p>
    {% if cta_text %}
      {% include 'components/button.html' with variant='primary' text=cta_text %}
    {% endif %}
  </div>
</div>
""")
    
    def generate_css_utilities(self):
        """Generate custom CSS utilities to supplement Tailwind."""
        print("\n" + "="*60)
        print("🎨 CUSTOM CSS UTILITIES (Add to your CSS)")
        print("="*60)
        
        print("""
/* static/css/utilities.css */
@layer utilities {
  /* Consistent spacing utilities */
  .section-spacing {
    @apply py-12 md:py-16 lg:py-20;
  }
  
  .content-spacing {
    @apply space-y-6 md:space-y-8;
  }
  
  /* Typography utilities */
  .text-display {
    @apply text-4xl md:text-5xl lg:text-6xl font-bold;
  }
  
  .text-heading {
    @apply text-2xl md:text-3xl lg:text-4xl font-semibold;
  }
  
  .text-subheading {
    @apply text-xl md:text-2xl font-medium;
  }
  
  /* Button utilities */
  .btn-base {
    @apply px-5 py-2.5 font-medium rounded-md transition-all duration-150 
           focus:outline-none focus:ring-2 focus:ring-offset-2;
  }
  
  .btn-primary {
    @apply btn-base bg-primary hover:bg-primary-hover text-white focus:ring-primary;
  }
  
  .btn-secondary {
    @apply btn-base bg-gray-200 hover:bg-gray-300 text-gray-800 focus:ring-gray-500;
  }
  
  /* Form utilities */
  .form-input {
    @apply w-full px-4 py-2 border border-gray-300 rounded-md 
           focus:ring-2 focus:ring-primary focus:border-primary 
           transition-colors duration-150;
  }
  
  /* Card utilities */
  .card {
    @apply bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow duration-200;
  }
  
  .card-body {
    @apply p-6;
  }
}
""")
    
    def generate_report(self, output_file='tailwind_consistency_report.json'):
        """Generate a detailed JSON report."""
        report = {
            'summary': {
                'total_pages_analyzed': len(set(elem['page'] for elems in self.results.values() for elem in elems)),
                'total_elements_analyzed': sum(len(elems) for elems in self.results.values()),
                'component_types_checked': list(self.results.keys()),
                'total_issues_found': len(self.inconsistencies)
            },
            'inconsistencies': [
                {'category': cat, 'issue': issue} 
                for cat, issue in self.inconsistencies
            ],
            'class_usage_stats': {
                component: dict(counter.most_common(10))
                for component, counter in self.class_usage.items()
            },
            'detailed_results': dict(self.results)
        }
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\n📊 Detailed report saved to: {output_file}")
        return report
    
    def close(self):
        """Close the web driver."""
        self.driver.quit()


def main():
    """Main function to run Tailwind consistency checker for Jersey Events."""
    
    # Initialize the checker
    checker = TailwindConsistencyChecker(
        base_url='http://localhost:8000',
        headless=False  # Set to True for headless mode
    )
    
    try:
        # Get all Django URLs
        django_urls = checker.get_django_urls()
        
        # Select pages to check
        pages_to_check = [
            ('home', django_urls['home']),
            ('events_list', django_urls['events_list']),
            ('about', django_urls['about']),
            ('login', django_urls['login']),
            ('register_customer', django_urls['register_customer']),
        ]
        
        print("🚀 Starting Tailwind CSS Consistency Check for Jersey Events")
        print(f"   Checking {len(pages_to_check)} pages...")
        
        # Analyze each page
        for page_name, url in pages_to_check:
            checker.check_page(url, page_name)
        
        # Find inconsistencies
        inconsistencies = checker.find_tailwind_inconsistencies()
        
        # Generate suggestions
        checker.generate_tailwind_config_suggestions()
        checker.generate_component_classes()
        checker.generate_css_utilities()
        
        # Generate report
        report = checker.generate_report('tailwind_consistency_report.json')
        
        # Final recommendations
        print("\n" + "="*60)
        print("✅ KEY RECOMMENDATIONS FOR TAILWIND CONSISTENCY")
        print("="*60)
        print("""
1. **Create Django template components** for reusable elements:
   - templates/components/button.html
   - templates/components/card.html
   - templates/components/heading.html

2. **Use consistent Tailwind classes** across pages:
   - Headers: text-4xl font-bold (H1), text-3xl font-semibold (H2)
   - Buttons: px-5 py-2.5 rounded-md
   - Containers: max-w-7xl mx-auto px-4 sm:px-6 lg:px-8

3. **Extend Tailwind config** with your brand values:
   - Define custom colors (primary, secondary)
   - Set consistent max-widths
   - Create typography scale

4. **Use @apply in CSS** for complex repeated patterns:
   - Create .btn-primary, .btn-secondary classes
   - Define .card and .card-body utilities

5. **Standardize spacing**:
   - Use consistent padding: p-6 for cards, py-12 for sections
   - Use space-y-* utilities for vertical spacing
   - Stick to Tailwind's default scale (4, 6, 8, 12, 16, etc.)
""")
        
        if inconsistencies:
            print(f"\n🔴 Found {len(inconsistencies)} inconsistency issues to fix")
        else:
            print("\n✨ Great! No major inconsistencies found")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        checker.close()


if __name__ == "__main__":
    main()