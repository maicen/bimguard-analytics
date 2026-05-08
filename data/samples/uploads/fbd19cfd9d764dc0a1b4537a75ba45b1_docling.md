
 Usage: docling [OPTIONS] source

docling --from pdf --to md --image-export-mode placeholder -v

+- Arguments ------------------------------------------------------------------------------------------------------------------------------------------------------+
| *    input_sources      source  PDF files to convert. Can be local file / directory paths or URL. [required]                                                     |
+------------------------------------------------------------------------------------------------------------------------------------------------------------------+
+- Options --------------------------------------------------------------------------------------------------------------------------------------------------------+
| --from                                                               [docx|pptx|html|image|pdf|asciidoc|md|csv|xl  Specify input formats to convert from.        |
|                                                                      sx|xml_uspto|xml_jats|xml_xbrl|mets_gbs|json  Defaults to all formats.                      |
|_docling|audio|vtt|latex]                                                                   |
| --to                                                                 [md|json|yaml|html|html_split_page|text|doct  Specify output formats. Defaults to Markdown. |
|                                                                      ags|vtt]                                                                                    |
| --show-layout                     --no-show-layout                                                                 If enabled, the page images will show the     |
|                                                                                                                    bounding-boxes of the items.                  |
|                                                                                                                    [default: no-show-layout]                     |
| --headers                                                            TEXT                                          Specify http request headers used when        |
|                                                                                                                    fetching url input sources in the form of a   |
|                                                                                                                    JSON string                                   |
| --image-export-mode                                                  [placeholder|embedded|referenced]             Image export mode for image-capable document  |
|                                                                                                                    outputs (JSON, YAML, HTML, HTML split-page,   |
|                                                                                                                    and Markdown). Text, DocTags, and WebVTT      |
|                                                                                                                    outputs do not export images. With            |
|                                                                                                                    `placeholder`, only the position of the image |
|                                                                                                                    is marked in the output. In `embedded` mode,  |
|                                                                                                                    the image is embedded as base64 encoded       |
|                                                                                                                    string. In `referenced` mode, the image is    |
|                                                                                                                    exported in PNG format and referenced from    |
|                                                                                                                    the main exported document.                   |
|                                                                                                                    [default: embedded]                           |
| --pipeline                                                           [legacy|standard|vlm|asr]                     Choose the pipeline to process PDF or image   |
|                                                                                                                    files.                                        |
|                                                                                                                    [default: standard]                           |
| --vlm-model                                                          TEXT                                          Choose the VLM preset to use with PDF or      |
|                                                                                                                    image files. Available presets: smoldocling,  |
|                                                                                                                    granite_docling, deepseek_ocr,                |
|                                                                                                                    granite_vision, pixtral, got_ocr, phi4, qwen, |
|                                                                                                                    gemma_12b, gemma_27b, dolphin, glm_ocr        |
|                                                                                                                    [default: granite_docling]                    |
| --asr-model                                                          [whisper_tiny|whisper_small|whisper_medium|w  Choose the ASR model to use with audio/video  |
|                                                                      hisper_base|whisper_large|whisper_turbo|whis  files.                                        |
|                                                                      per_tiny_mlx|whisper_small_mlx|whisper_mediu  [default: whisper_tiny]                       |
|                                                                      m_mlx|whisper_base_mlx|whisper_large_mlx|whi                                                |
|                                                                      sper_turbo_mlx|whisper_tiny_native|whisper_s                                                |
|                                                                      mall_native|whisper_medium_native|whisper_ba                                                |
|                                                                      se_native|whisper_large_native|whisper_turbo                                                |
|                                                                      _native]                                                                                    |
| --ocr                             --no-ocr                                                                         If enabled, the bitmap content will be        |
|                                                                                                                    processed using OCR.                          |
|                                                                                                                    [default: ocr]                                |
| --force-ocr                       --no-force-ocr                                                                   Replace any existing text with OCR generated  |
|                                                                                                                    text over the full content.                   |
|                                                                                                                    [default: no-force-ocr]                       |
| --tables                          --no-tables                                                                      If enabled, the table structure model will be |
|                                                                                                                    used to extract table information.            |
|                                                                                                                    [default: tables]                             |
| --ocr-engine                                                         TEXT                                          The OCR engine to use. When                   |
|                                                                                                                    --allow-external-plugins is _not_ set, the    |
|                                                                                                                    available values are: auto, easyocr,          |
|                                                                                                                    kserve_v2_ocr, ocrmac, rapidocr, tesserocr,   |
|                                                                                                                    tesseract. Use the option                     |
|                                                                                                                    --show-external-plugins to see the options    |
|                                                                                                                    allowed with external plugins.                |
|                                                                                                                    [default: auto]                               |
| --ocr-lang                                                           TEXT                                          Provide a comma-separated list of languages   |
|                                                                                                                    used by the OCR engine. Note that each OCR    |
|                                                                                                                    engine has different values for the language  |
|                                                                                                                    names.                                        |
| --psm                                                                INTEGER                                       Page Segmentation Mode for the OCR engine     |
|                                                                                                                    (0-13).                                       |
| --pdf-backend                                                        [pypdfium2|docling_parse|dlparse_v1|dlparse_  The PDF backend to use.                       |
|                                                                      v2|dlparse_v4]                                [default: docling_parse]                      |
| --pdf-password                                                       TEXT                                          Password for protected PDF documents          |
| --table-mode                                                         [fast|accurate]                               The mode to use in the table structure model. |
|                                                                                                                    [default: accurate]                           |
| --enrich-code                     --no-enrich-code                                                                 Enable the code enrichment model in the       |
|                                                                                                                    pipeline.                                     |
|                                                                                                                    [default: no-enrich-code]                     |
| --enrich-formula                  --no-enrich-formula                                                              Enable the formula enrichment model in the    |
|                                                                                                                    pipeline.                                     |
|                                                                                                                    [default: no-enrich-formula]                  |
| --enrich-picture-classes          --no-enrich-picture-classes                                                      Enable the picture classification enrichment  |
|                                                                                                                    model in the pipeline.                        |
|                                                                                                                    [default: no-enrich-picture-classes]          |
| --enrich-picture-description      --no-enrich-picture-description                                                  Enable the picture description model in the   |
|                                                                                                                    pipeline.                                     |
|                                                                                                                    [default: no-enrich-picture-description]      |
| --enrich-chart-extraction         --no-enrich-chart-extraction                                                     Enable chart extraction to convert bar, pie,  |
|                                                                                                                    and line charts to tabular format.            |
|                                                                                                                    [default: no-enrich-chart-extraction]         |
| --artifacts-path                                                     PATH                                          If provided, the location of the model        |
|                                                                                                                    artifacts.                                    |
| --enable-remote-services          --no-enable-remote-services                                                      Must be enabled when using models connecting  |
|                                                                                                                    to remote services.                           |
|                                                                                                                    [default: no-enable-remote-services]          |
| --allow-external-plugins          --no-allow-external-plugins                                                      Must be enabled for loading modules from      |
|                                                                                                                    third-party plugins.                          |
|                                                                                                                    [default: no-allow-external-plugins]          |
| --show-external-plugins           --no-show-external-plugins                                                       List the third-party plugins which are        |
|                                                                                                                    available when the option                     |
|                                                                                                                    --allow-external-plugins is set.              |
|                                                                                                                    [default: no-show-external-plugins]           |
| --abort-on-error                  --no-abort-on-error                                                              If enabled, the processing will be aborted    |
|                                                                                                                    when the first error is encountered.          |
|                                                                                                                    [default: no-abort-on-error]                  |
| --output                                                             PATH                                          Output directory where results are saved.     |
|                                                                                                                    [default: .]                                  |
| --verbose                     -v                                     INTEGER                                       Set the verbosity level. -v for info logging, |
|                                                                                                                    -vv for debug logging.                        |
|                                                                                                                    [default: 0]                                  |
| --debug-visualize-cells           --no-debug-visualize-cells                                                       Enable debug output which visualizes the PDF  |
|                                                                                                                    cells                                         |
|                                                                                                                    [default: no-debug-visualize-cells]           |
| --debug-visualize-ocr             --no-debug-visualize-ocr                                                         Enable debug output which visualizes the OCR  |
|                                                                                                                    cells                                         |
|                                                                                                                    [default: no-debug-visualize-ocr]             |
| --debug-visualize-layout          --no-debug-visualize-layout                                                      Enable debug output which visualizes the      |
|                                                                                                                    layour clusters                               |
|                                                                                                                    [default: no-debug-visualize-layout]          |
| --debug-visualize-tables          --no-debug-visualize-tables                                                      Enable debug output which visualizes the      |
|                                                                                                                    table cells                                   |
|                                                                                                                    [default: no-debug-visualize-tables]          |
| --version                                                                                                          Show version information.                     |
| --document-timeout                                                   FLOAT                                         The timeout for processing each document, in  |
|                                                                                                                    seconds.                                      |
| --num-threads                                                        INTEGER                                       Number of threads [default: 4]                |
| --device                                                             [auto|cpu|cuda|mps|xpu]                       Accelerator device [default: auto]            |
| --logo                                                                                                             Docling logo                                  |
| --page-batch-size                                                    INTEGER                                       Number of pages processed in one batch.       |
|                                                                                                                    Default: 4                                    |
|                                                                                                                    [default: 4]                                  |
| --profiling                       --no-profiling                                                                   If enabled, it summarizes profiling details   |
|                                                                                                                    for all conversion stages.                    |
|                                                                                                                    [default: no-profiling]                       |
| --save-profiling                  --no-save-profiling                                                              If enabled, it saves the profiling summaries  |
|                                                                                                                    to json.                                      |
|                                                                                                                    [default: no-save-profiling]                  |
| --help                                                                                                             Show this message and exit.                   |
+------------------------------------------------------------------------------------------------------------------------------------------------------------------+
