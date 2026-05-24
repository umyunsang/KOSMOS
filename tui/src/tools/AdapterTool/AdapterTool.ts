import { z } from 'zod/v4'
import {
  buildTool,
  type Tool,
  type ToolDef,
  type ToolInputJSONSchema,
  type Tools,
} from '../../Tool.js'
import {
  listAdapters,
  resolveAdapter,
  type AdapterManifestEntry,
} from '../../services/api/adapterManifest.js'
import { getOrCreateUmmayaBridge } from '../../ipc/bridgeSingleton.js'
import { getOrCreatePendingCallRegistry } from '../../ipc/pendingCallSingleton.js'
import { dispatchPrimitive } from '../_shared/dispatchPrimitive.js'
import { LookupPrimitive } from '../LookupPrimitive/LookupPrimitive.js'
import { ResolveLocationPrimitive } from '../ResolveLocationPrimitive/ResolveLocationPrimitive.js'
import { SubmitPrimitive } from '../SubmitPrimitive/SubmitPrimitive.js'
import { VerifyPrimitive } from '../VerifyPrimitive/VerifyPrimitive.js'

type AdapterPrimitive = 'find' | 'locate' | 'send' | 'check'

type InputSchema = z.ZodType<{ [key: string]: unknown }>

const fallbackInputSchema = z.object({}).passthrough() as InputSchema

type JsonObject = Record<string, unknown>

function isJsonObject(value: unknown): value is JsonObject {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function asJsonObject(value: unknown): JsonObject {
  return isJsonObject(value) ? value : {}
}

function asStringArray(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === 'string')
    : []
}

function schemaDescription(schema: JsonObject): string | undefined {
  return typeof schema.description === 'string' && schema.description.trim()
    ? schema.description
    : undefined
}

function applyJsonSchemaMetadata(schema: z.ZodTypeAny, jsonSchema: JsonObject): z.ZodTypeAny {
  let result = schema
  const description = schemaDescription(jsonSchema)
  if (description) {
    result = result.describe(description)
  }
  if (Object.prototype.hasOwnProperty.call(jsonSchema, 'default')) {
    result = result.default(jsonSchema.default)
  }
  return result
}

function zodUnion(schemas: z.ZodTypeAny[]): z.ZodTypeAny {
  if (schemas.length === 0) {
    return z.unknown()
  }
  if (schemas.length === 1) {
    return schemas[0] ?? z.unknown()
  }
  return z.union(schemas as [z.ZodTypeAny, z.ZodTypeAny, ...z.ZodTypeAny[]])
}

function zodLiteralUnion(values: unknown[]): z.ZodTypeAny {
  const literals = values.map(value => z.literal(value as string | number | boolean | null))
  return zodUnion(literals)
}

function resolveRef(root: JsonObject, ref: string): JsonObject | undefined {
  if (!ref.startsWith('#/$defs/')) {
    return undefined
  }
  const defName = decodeURIComponent(ref.slice('#/$defs/'.length))
  const defs = asJsonObject(root.$defs)
  const resolved = defs[defName]
  return isJsonObject(resolved) ? resolved : undefined
}

function zodFromJsonSchema(schema: JsonObject, root: JsonObject): z.ZodTypeAny {
  if (typeof schema.$ref === 'string') {
    const resolved = resolveRef(root, schema.$ref)
    if (resolved) {
      return applyJsonSchemaMetadata(zodFromJsonSchema(resolved, root), schema)
    }
  }

  const variants = Array.isArray(schema.anyOf)
    ? schema.anyOf
    : Array.isArray(schema.oneOf)
      ? schema.oneOf
      : undefined
  if (variants) {
    const variantSchemas = variants
      .filter(isJsonObject)
      .map(variant => zodFromJsonSchema(variant, root))
    return applyJsonSchemaMetadata(zodUnion(variantSchemas), schema)
  }

  if (Array.isArray(schema.enum) && schema.enum.length > 0) {
    return applyJsonSchemaMetadata(zodLiteralUnion(schema.enum), schema)
  }

  if (Object.prototype.hasOwnProperty.call(schema, 'const')) {
    return applyJsonSchemaMetadata(
      z.literal(schema.const as string | number | boolean | null),
      schema,
    )
  }

  const typeValue = schema.type
  if (Array.isArray(typeValue)) {
    const nonNullTypes = typeValue.filter(item => item !== 'null')
    const nullable = nonNullTypes.length !== typeValue.length
    const typedSchemas = nonNullTypes.map(typeName =>
      zodFromJsonSchema({ ...schema, type: typeName }, root),
    )
    const base = zodUnion(typedSchemas)
    return applyJsonSchemaMetadata(nullable ? base.nullable() : base, schema)
  }

  switch (typeValue) {
    case 'string':
      return applyJsonSchemaMetadata(z.string(), schema)
    case 'integer':
      return applyJsonSchemaMetadata(z.number().int(), schema)
    case 'number':
      return applyJsonSchemaMetadata(z.number(), schema)
    case 'boolean':
      return applyJsonSchemaMetadata(z.boolean(), schema)
    case 'array': {
      const itemSchema = isJsonObject(schema.items)
        ? zodFromJsonSchema(schema.items, root)
        : z.unknown()
      return applyJsonSchemaMetadata(z.array(itemSchema), schema)
    }
    case 'object': {
      const properties = asJsonObject(schema.properties)
      const required = new Set(asStringArray(schema.required))
      const shape: Record<string, z.ZodTypeAny> = {}
      for (const [propertyName, propertySchemaRaw] of Object.entries(properties)) {
        const propertySchema = asJsonObject(propertySchemaRaw)
        let fieldSchema = zodFromJsonSchema(propertySchema, root)
        if (
          !required.has(propertyName) &&
          !Object.prototype.hasOwnProperty.call(propertySchema, 'default')
        ) {
          fieldSchema = fieldSchema.optional()
        }
        shape[propertyName] = fieldSchema
      }
      const objectSchema =
        schema.additionalProperties === false
          ? z.object(shape).strict()
          : z.object(shape).passthrough()
      return applyJsonSchemaMetadata(objectSchema, schema)
    }
    case 'null':
      return applyJsonSchemaMetadata(z.null(), schema)
    default:
      return applyJsonSchemaMetadata(z.unknown(), schema)
  }
}

function inputSchemaFor(entry: AdapterManifestEntry): InputSchema {
  const schema = asJsonObject(entry.input_schema_json)
  if (schema.type !== 'object') {
    return fallbackInputSchema
  }
  return zodFromJsonSchema(schema, schema) as InputSchema
}

function inputJSONSchemaFor(entry: AdapterManifestEntry): ToolInputJSONSchema | undefined {
  const schema = asJsonObject(entry.input_schema_json)
  if (schema.type !== 'object') {
    return undefined
  }
  return schema as ToolInputJSONSchema
}

function primitiveFor(entry: AdapterManifestEntry): AdapterPrimitive {
  return entry.primitive as AdapterPrimitive
}

function primitiveToolFor(primitive: AdapterPrimitive): Tool {
  switch (primitive) {
    case 'locate':
      return ResolveLocationPrimitive as Tool
    case 'send':
      return SubmitPrimitive as Tool
    case 'check':
      return VerifyPrimitive as Tool
    case 'find':
    default:
      return LookupPrimitive as Tool
  }
}

function rootInputFor(entry: AdapterManifestEntry, input: Record<string, unknown>) {
  return {
    tool_id: entry.tool_id,
    params: input,
  }
}

export function isAdapterToolName(name: string): boolean {
  return resolveAdapter(name) !== undefined
}

export function getAdapterToolByName(name: string): Tool | undefined {
  const entry = resolveAdapter(name)
  return entry ? buildAdapterTool(entry) : undefined
}

export function getAdapterTools(): Tools {
  return listAdapters().map(buildAdapterTool)
}

function buildAdapterTool(entry: AdapterManifestEntry): Tool {
  const primitive = primitiveFor(entry)
  const primitiveTool = primitiveToolFor(primitive)
  const adapterInputSchema = inputSchemaFor(entry)
  const adapterInputJSONSchema = inputJSONSchemaFor(entry)

  return buildTool({
    name: entry.tool_id,
    // K-EXAONE runs through FriendliAI's OpenAI-compatible function calling,
    // not Anthropic tool_reference. Keep CC's Tool object shape, but make the
    // concrete public-service adapter schemas visible on the first turn.
    alwaysLoad: true,
    searchHint: [entry.search_hint, entry.name, entry.tool_id, primitive]
      .filter(Boolean)
      .join(' '),
    maxResultSizeChars: primitiveTool.maxResultSizeChars,
    inputJSONSchema: adapterInputJSONSchema,

    get inputSchema(): InputSchema {
      return adapterInputSchema
    },

    get outputSchema() {
      return primitiveTool.outputSchema
    },

    isEnabled() {
      return true
    },

    isConcurrencySafe(input) {
      return primitiveTool.isConcurrencySafe(rootInputFor(entry, input))
    },

    isReadOnly(input) {
      return primitiveTool.isReadOnly(rootInputFor(entry, input))
    },

    isDestructive(input) {
      return primitiveTool.isDestructive?.(rootInputFor(entry, input)) ?? false
    },

    async description() {
      return entry.name
    },

    async prompt() {
      const description = entry.llm_description?.trim() || `${entry.name}.`
      return [
        description,
        `Concrete UMMAYA ${primitive} adapter. Call this tool directly with the ` +
          'adapter schema arguments supplied by the backend manifest.',
      ].join('\n\n')
    },

    async validateInput(input) {
      if (!resolveAdapter(entry.tool_id)) {
        return {
          result: false as const,
          message: `Adapter '${entry.tool_id}' is not in the synced backend manifest.`,
          errorCode: 1,
        }
      }
      if (typeof input !== 'object' || input === null) {
        return {
          result: false as const,
          message: `Adapter '${entry.tool_id}' expects a JSON object argument.`,
          errorCode: 1,
        }
      }
      return { result: true as const }
    },

    async call(input, context) {
      return dispatchPrimitive({
        primitive,
        toolName: entry.tool_id,
        args: input,
        context,
        registry: getOrCreatePendingCallRegistry(),
        bridge: getOrCreateUmmayaBridge(),
      })
    },

    userFacingName(input) {
      return primitiveTool.userFacingName(rootInputFor(entry, input ?? {}))
    },

    mapToolResultToToolResultBlockParam(output, toolUseID) {
      return primitiveTool.mapToolResultToToolResultBlockParam(output, toolUseID)
    },

    renderToolUseMessage(input, options) {
      const rendered = primitiveTool.renderToolUseMessage(
        rootInputFor(entry, input),
        options,
      )
      return rendered === null ? entry.tool_id : rendered
    },

    renderToolResultMessage(output, progressMessagesForMessage, options) {
      return primitiveTool.renderToolResultMessage?.(
        output,
        progressMessagesForMessage,
        options,
      ) ?? null
    },

    isResultTruncated(output) {
      return primitiveTool.isResultTruncated?.(output) ?? false
    },
  } satisfies ToolDef<InputSchema>)
}
