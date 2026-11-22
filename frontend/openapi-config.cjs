/** @type {import('@rtk-query/codegen-openapi').ConfigFile} */
module.exports = {
  schemaFile: './openapi.json',
  apiFile: './src/api/baseApi.ts',
  apiImport: 'baseApi',
  outputFile: './src/api/generated.ts',
  exportName: 'mentatApi',
  hooks: true,
  tag: true,
}
