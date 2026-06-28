# Project Guidelines

This is a React.js app with SCSS styles.

## File Structure

- All React components should be placed in `src/App.jsx`
- All styles should be placed in `src/App.scss`

This single-file approach is intentional for rapid prototyping. Refactor into multiple files as the prototype grows.

## CSS/SCSS Conventions

- Use BEM (Block Element Modifier) naming methodology for CSS classes
- Follow the pattern: `.block__element--modifier`
- Use SCSS nesting with `&` for better organization
- Leverage CSS custom properties for theming

### BEM Example

```scss
.card {
  background: var(--color-bg);
  padding: var(--spacing-2x);

  &__header {
    border-bottom: 1px solid var(--color-text-light);
  }

  &__title {
    font-size: var(--font-size-xl);

    &--large {
      font-size: calc(var(--font-size-xl) * 1.5);
    }
  }
}
```

```jsx
<div className="card">
  <div className="card__header">
    <h2 className="card__title card__title--large">Title</h2>
  </div>
</div>
```

## CSS Custom Properties

Available variables defined in `src/App.scss`:

- `--color-text`, `--color-text-light`, `--color-bg`
- `--font-size-base`, `--font-size-xl`
- `--spacing-unit`, `--spacing-2x`, `--spacing-3x`

## Environment Variables

- Copy `.env.example` to `.env.local` for local configuration
- All Vite environment variables must be prefixed with `VITE_`
- Access in code: `import.meta.env.VITE_API_URL`

Example:

```jsx
const apiUrl = import.meta.env.VITE_API_URL || "http://localhost:3000";
```
