/**
 * End-to-end tests for the Ideas page
 */
describe('Ideas Page', () => {
  beforeEach(() => {
    cy.visit('/ideas');

    cy.contains('Investment Ideas', { timeout: 10000 }).should('be.visible');
  });

  it('displays ideas from the API', () => {
    cy.get('[data-testid="idea-card"]').should('have.length.at.least', 1);
  });

  it('selects a company suggestion and updates the URL', () => {
    cy.get('[data-testid="company-search"]').type('Apple');
    cy.get('[data-testid="company-option"]').first().click();
    cy.url().should('include', 'company_id=');
  });

  it('applies position filters from the drawer', () => {
    cy.get('[aria-label="Open filters"]').click();
    cy.get('[aria-label="Position"]').select('short');
    cy.contains('button', 'Apply filters').click();
    cy.url().should('include', 'is_short=true');
    cy.contains('Short ideas').should('be.visible');
  });

  it('discards unapplied drawer changes', () => {
    cy.url().then(urlBefore => {
      cy.get('[aria-label="Open filters"]').click();
      cy.get('[aria-label="Position"]').select('short');
      cy.get('[aria-label="Close"]').click();
      cy.url().should('eq', urlBefore);
    });
  });

  it('loads more ideas', () => {
    cy.get('[data-testid="idea-card"]').then($initialCards => {
      const initialCount = $initialCards.length;

      cy.get('[data-testid="load-more-button"]').scrollIntoView().click();
      cy.get('[data-testid="idea-card"]').should('have.length.greaterThan', initialCount);
    });
  });
});

describe('Idea Detail Page', () => {
  it('displays idea details when clicking on an idea card', () => {
    // Visit the ideas page
    cy.visit('/ideas');
    
    // Wait for ideas to load
    cy.get('[data-testid="idea-card"]').should('have.length.at.least', 1);
    
    // Click on the first idea
    cy.get('[data-testid="idea-card"]').first().click();
    
    // Verify navigation to detail page
    cy.url().should('include', '/ideas/');
    
    // Check if detail components are displayed
    cy.contains('Investment Thesis').should('be.visible');
    cy.contains('Catalysts').should('exist');
    cy.contains('Performance').should('exist');
  });
});

describe('Navigation', () => {
  it('navigates between main pages', () => {
    // Start at home page
    cy.visit('/');
    
    // Go to ideas page
    cy.contains('Ideas').click();
    cy.url().should('include', '/ideas');
    
    // Go to companies page
    cy.contains('Companies').click();
    cy.url().should('include', '/companies');
    
    // Go to users page
    cy.contains('Users').click();
    cy.url().should('include', '/users');
    
    // Go back to home
    cy.contains('Home').click();
    cy.url().should('not.include', '/ideas');
  });
});
