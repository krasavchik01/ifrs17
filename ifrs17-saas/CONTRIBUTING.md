# Contributing to IFRS 17 Pro

Thank you for your interest in contributing to IFRS 17 Pro! This document provides guidelines and instructions for contributing.

## 🎯 Ways to Contribute

- **Bug Reports**: Found a bug? Please report it!
- **Feature Requests**: Have an idea? We'd love to hear it!
- **Code Contributions**: Submit pull requests
- **Documentation**: Improve our docs
- **Testing**: Help test new features
- **Translations**: Add support for more languages

## 🚀 Getting Started

### 1. Fork the Repository

Click the "Fork" button at the top right of the repository page.

### 2. Clone Your Fork

```bash
git clone https://github.com/YOUR_USERNAME/ifrs17-saas.git
cd ifrs17-saas
```

### 3. Set Up Development Environment

```bash
# Install dependencies
npm install

# Copy environment variables
cp .env.example .env

# Set up database
npx prisma migrate dev

# Run development server
npm run dev
```

### 4. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/bug-description
```

## 📝 Coding Standards

### TypeScript

- Use TypeScript for all new code
- Enable strict mode
- Avoid `any` types when possible
- Document complex types with comments

### Code Style

We use ESLint and Prettier for code formatting:

```bash
# Check linting
npm run lint

# Format code
npm run format
```

### Naming Conventions

- **Files**: `kebab-case.ts`
- **Components**: `PascalCase.tsx`
- **Functions**: `camelCase()`
- **Constants**: `UPPER_SNAKE_CASE`
- **Interfaces**: `PascalCase` (no I prefix)

### Example

```typescript
// Good
interface UserProfile {
  id: string;
  email: string;
}

function calculateCSM(contract: Contract): number {
  // Implementation
}

const MAX_CONTRACTS = 10000;

// Bad
interface IUserProfile { } // Don't use I prefix
function CalculateCSM() { } // Should be camelCase
const maxContracts = 10000; // Should be UPPER_SNAKE_CASE for constants
```

## 🏗️ Project Structure

```
src/
├── app/                 # Next.js App Router pages
│   ├── api/            # API routes
│   ├── dashboard/      # Dashboard pages
│   └── ...
├── components/         # React components
│   └── ui/            # Reusable UI components
├── lib/               # Utility libraries
│   ├── ifrs17/        # IFRS 17 calculation engines
│   ├── auth.ts        # Authentication
│   └── prisma.ts      # Database client
└── types/             # TypeScript type definitions
```

## 🧪 Testing

### Running Tests

```bash
# Unit tests
npm run test

# E2E tests
npm run test:e2e

# Coverage
npm run test:coverage
```

### Writing Tests

```typescript
import { describe, it, expect } from '@jest/globals';
import { calculateCSM } from '@/lib/ifrs17/csm';

describe('CSM Calculations', () => {
  it('should calculate initial CSM correctly', () => {
    const result = calculateCSM({
      inflows: 100000,
      outflows: 80000,
      riskAdjustment: 5000,
    });

    expect(result).toBe(15000);
  });
});
```

## 📋 Commit Guidelines

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

### Examples

```bash
feat(csm): add support for VFA measurement model

fix(auth): resolve session timeout issue

docs(readme): update installation instructions

refactor(contracts): optimize query performance
```

## 🔄 Pull Request Process

### 1. Before Submitting

- [ ] Code follows style guidelines
- [ ] Tests pass (`npm run test`)
- [ ] Linting passes (`npm run lint`)
- [ ] Documentation is updated
- [ ] Commit messages follow conventions
- [ ] Branch is up to date with main

### 2. Submit PR

1. Push your branch to GitHub
2. Open a Pull Request
3. Fill out the PR template
4. Link related issues

### 3. PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] E2E tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No new warnings
```

### 4. Review Process

- Maintainers will review within 48 hours
- Address feedback and update PR
- Once approved, PR will be merged

## 🐛 Reporting Bugs

### Before Reporting

1. Check existing issues
2. Verify it's reproducible
3. Test on latest version

### Bug Report Template

```markdown
**Describe the bug**
Clear description of the bug

**To Reproduce**
Steps to reproduce:
1. Go to '...'
2. Click on '...'
3. See error

**Expected behavior**
What should happen

**Screenshots**
If applicable

**Environment**
- OS: [e.g., macOS]
- Browser: [e.g., Chrome 120]
- Version: [e.g., 1.0.0]

**Additional context**
Any other information
```

## 💡 Feature Requests

### Feature Request Template

```markdown
**Is your feature related to a problem?**
Description of the problem

**Describe the solution**
How should it work?

**Alternatives considered**
Other approaches you've considered

**Additional context**
Screenshots, mockups, examples
```

## 📚 Documentation

### Improving Docs

- Fix typos and errors
- Add examples
- Clarify confusing sections
- Add translations

### Documentation Style

- Use clear, concise language
- Include code examples
- Add screenshots where helpful
- Keep consistent formatting

## 🌍 Internationalization

### Adding Translations

1. Add translation files in `src/locales/[lang].json`
2. Use translation keys consistently
3. Test with different languages

Example:

```json
{
  "dashboard.title": "Dashboard",
  "contracts.create": "Create Contract",
  "errors.notFound": "Not found"
}
```

## 🔐 Security

### Reporting Security Issues

**DO NOT** open public issues for security vulnerabilities.

Email: security@ifrs17pro.com

Include:
- Description of vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

## 📄 License

By contributing, you agree that your contributions will be licensed under the project's license.

## 🤝 Code of Conduct

### Our Pledge

We pledge to make participation in our project a harassment-free experience for everyone.

### Standards

- Use welcoming and inclusive language
- Be respectful of differing viewpoints
- Accept constructive criticism gracefully
- Focus on what's best for the community

### Enforcement

Violations can be reported to: conduct@ifrs17pro.com

## 💬 Communication

- **GitHub Issues**: Bug reports, feature requests
- **GitHub Discussions**: General questions, ideas
- **Discord**: Real-time chat
- **Email**: support@ifrs17pro.com

## 🎓 Resources

- [Next.js Documentation](https://nextjs.org/docs)
- [TypeScript Documentation](https://www.typescriptlang.org/docs)
- [Prisma Documentation](https://www.prisma.io/docs)
- [IFRS 17 Standard](https://www.ifrs.org/issued-standards/list-of-standards/ifrs-17-insurance-contracts/)

## ❓ Questions?

Feel free to:
- Open a discussion on GitHub
- Join our Discord community
- Email: support@ifrs17pro.com

---

Thank you for contributing to IFRS 17 Pro! 🎉
