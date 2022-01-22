module.exports = {
  async haeders() {
    return [
      {
        source: '/data/geojson_data.json',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=100, must-revalidate'
          }
        ]
      }
    ]
  },
  typescript: {
    ignoreBuildErrors: true
  }
}
