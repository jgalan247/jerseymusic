
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
