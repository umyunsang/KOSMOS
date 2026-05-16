# Usage notes: 헌법재판소_발간자료 조회 서비스

Official detail page: https://www.data.go.kr/data/15140950/openapi.do

## Base URL

```text
https://apis.data.go.kr/9750000/PubDocsService
```

The page also lists HTTP as an allowed scheme in the embedded Swagger, but UMMAYA should prefer HTTPS.

## Operations

### `GET /getSerialPublicationList`

Purpose: search major serial publications by title or content.

Required query parameters:

- `serviceKey`: data.go.kr issued service key

Optional query parameters:

- `pageNo`: page number
- `numOfRows`: rows per page
- `type`: response format, `xml` or `json`; default `xml`
- `fields`: comma-separated fields to expose; default all fields
- `title`: serial publication title
- `content`: content keyword

Useful response fields:

- `seqNo`: book serial number
- `title`: title
- `pubFreq`: publication frequency
- `pubDate`: volume/year statement
- `bookImg`: book image link
- `content`: content
- `totalCount`, `pageNo`, `numOfRows`, `resultCode`, `resultMsg`

### `GET /getSerialPublicationDetail`

Purpose: retrieve serial-publication detail records by book serial number.

Required query parameters:

- `serviceKey`: data.go.kr issued service key
- `seqNo`: book serial number returned by serial-publication list search

Optional query parameters:

- `pageNo`
- `numOfRows`
- `type`
- `fields`

Useful response fields:

- `seqNo`: requested book serial number
- `subSeq`: book volume serial number
- `title`: title plus volume number
- `fileLink1`: original file link used when the material was published
- `fileLink2`: Korean-converted file link for easier understanding

### `GET /getPblctLtrtreList`

Purpose: search publication literature by title/name, series, author/reporter, or content.

Required query parameters:

- `serviceKey`: data.go.kr issued service key

Optional query parameters:

- `pageNo`
- `numOfRows`
- `type`
- `fields`
- `title`: publication title/name
- `book`: publication series
- `bookReporter`: author/reporter
- `xmlContent`: content keyword

Useful response fields:

- `bookInfoSeq`: literature serial number
- `title`: title
- `book`: series
- `bookReporter`: author/reporter
- `bookSection`: classification
- `volumeInfo`: bibliographic information
- `publisher`: publisher
- `pressDate`: publication date

### `GET /getPblctLtrtreDetail`

Purpose: retrieve publication literature detail by literature serial number.

Required query parameters:

- `serviceKey`: data.go.kr issued service key
- `bookInfoSeq`: literature serial number returned by publication list search

Optional query parameters:

- `pageNo`
- `numOfRows`
- `type`
- `fields`

Useful response fields:

- `xmlContent`
- `bookInfoSeq`
- `title`
- `book`
- `bookReporter`
- `publisher`
- `pressDate`
- `bookSection`
- `volumeInfo`
- `seriesInfo`
- `startPage`
- `endPage`

## UMMAYA primitive contract sketch

Input envelope:

```json
{
  "primitive": "lookup",
  "adapter": "ccourt_publication_documents",
  "query": {
    "collection": "serial_publication | publication_literature | auto",
    "title": "기본권",
    "content": "평등권",
    "author": null,
    "identifier": null,
    "page": 1,
    "rows": 10
  }
}
```

Routing:

- If `identifier.seqNo` exists, call `/getSerialPublicationDetail`.
- If `identifier.bookInfoSeq` exists, call `/getPblctLtrtreDetail`.
- If only topic/title/content terms exist, call list operations and rank locally.
- If the user asks for original files, include `fileLink1`/`fileLink2` only from the official detail response.

## Live validation status

No live endpoint probe was performed in this collection unit. Before implementation as a live UMMAYA adapter, validate the endpoint, service key encoding, `type=json`, and required identifier parameters with direct `curl` probes and sanitized request/response artifacts.

