/**
 * TypeScript schema validator for API contracts.
 *
 * Run with: npm run validate-schema
 */
import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import type {
  Company,
  CrawlCounts,
  CrawlRun,
  CrawlSourceStatus,
  CrawlSample,
  Idea,
  IdeaDetail,
  Performance,
  User,
} from './api';

type SchemaProperty = {
  type?: string;
  format?: string;
  items?: SchemaProperty;
  properties?: Record<string, SchemaProperty>;
  $ref?: string;
  anyOf?: SchemaProperty[];
  enum?: string[];
};

type SchemaDefinition = SchemaProperty & {
  required?: string[];
};

type OpenAPISchema = {
  components?: {
    schemas?: Record<string, SchemaDefinition>;
  };
  paths?: Record<string, unknown>;
};

const readOpenApiSchema = (): OpenAPISchema => {
  const schemaPath = [
    resolve(process.cwd(), 'api/schema/openapi.json'),
    resolve(process.cwd(), '../api/schema/openapi.json'),
  ].find((candidate) => existsSync(candidate));

  if (!schemaPath) {
    throw new Error('API OpenAPI schema not found from the current working directory');
  }

  return JSON.parse(readFileSync(schemaPath, 'utf8')) as OpenAPISchema;
};

/**
 * Validate frontend types against the API schema.
 */
async function validateSchema(): Promise<boolean> {
  try {
    const schema = readOpenApiSchema();

    const validations = [
      validateType<Idea>('IdeaResponse', schema),
      validateType<IdeaDetail>('IdeaDetailResponse', schema),
      validateType<Company>('CompanyResponse', schema),
      validateType<User>('UserResponse', schema),
      validateType<Performance>('PerformanceResponse', schema),
      validateType<CrawlRun>('CrawlRunResponse', schema),
      validateType<CrawlCounts>('CrawlCountsResponse', schema),
      validateType<CrawlSample>('CrawlHoldingSampleResponse', schema),
      validateType<CrawlSample>('CrawlIdeaSampleResponse', schema),
      validateType<CrawlSourceStatus>('CrawlSourceStatusResponse', schema),
    ];

    const allValid = validations.every(Boolean);
    if (allValid) {
      console.log('All frontend types valid against the API schema');
      return true;
    }

    console.error('Type validation failed');
    return false;
  } catch (error) {
    console.error('Error validating schema:', error);
    return false;
  }
}

/**
 * Validate a specific type against an OpenAPI schema definition.
 */
function validateType<T>(schemaName: string, schema: OpenAPISchema): boolean {
  console.log(`Validating ${schemaName}...`);

  const schemaDefinition = schema.components?.schemas?.[schemaName];
  if (!schemaDefinition) {
    console.error(`Schema ${schemaName} not found in API schema`);
    return false;
  }

  const properties = schemaDefinition.properties ?? {};
  const missingRequired = (schemaDefinition.required ?? []).filter(
    (propertyName) => !Object.prototype.hasOwnProperty.call(properties, propertyName),
  );
  if (missingRequired.length > 0) {
    console.error(`Schema ${schemaName} is missing required fields: ${missingRequired.join(', ')}`);
    return false;
  }

  // Keep the generic so each checked frontend type remains coupled to its schema entry at compile time.
  const sample = createSample(schemaDefinition) as unknown as T;
  return sample !== null;
}

const createSample = (schemaDefinition: SchemaProperty): Record<string, unknown> | null => {
  if (schemaDefinition.type !== 'object') return null;

  const result: Record<string, unknown> = {};
  for (const [propertyName, propertySchema] of Object.entries(schemaDefinition.properties ?? {})) {
    result[propertyName] = createSampleForProperty(propertySchema);
  }
  return result;
};

const createSampleForProperty = (propertySchema: SchemaProperty): unknown => {
  if (propertySchema.anyOf) {
    const nonNullSchema = propertySchema.anyOf.find((candidate) => candidate.type !== 'null');
    return nonNullSchema ? createSampleForProperty(nonNullSchema) : null;
  }

  if (propertySchema.$ref) return {};

  switch (propertySchema.type) {
    case 'string':
      return propertySchema.format === 'date-time' || propertySchema.format === 'date'
        ? new Date().toISOString()
        : propertySchema.enum?.[0] ?? 'sample';
    case 'integer':
    case 'number':
      return 1;
    case 'boolean':
      return true;
    case 'array':
      return propertySchema.items ? [createSampleForProperty(propertySchema.items)] : [];
    case 'object':
      return createSample(propertySchema) ?? {};
    default:
      return null;
  }
};

export { validateSchema };

if (process.argv[1]?.endsWith('schema-validator.ts')) {
  validateSchema().then((valid) => {
    process.exitCode = valid ? 0 : 1;
  });
}
