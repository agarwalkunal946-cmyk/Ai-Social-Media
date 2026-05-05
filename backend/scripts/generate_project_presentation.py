from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from textwrap import dedent
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "Synapse-AI-Social-Media-Presentation.pptx"

SLIDES = [
    {
        "title": "Synapse AI Social Media Analytics",
        "subtitle": "Final year project presentation",
        "bullets": [
            "AI-powered analytics platform for Instagram, YouTube, and X / Twitter",
            "Built with React, FastAPI, MongoDB, Redis / Memurai, and Firebase Authentication",
            "Combines dashboard analytics, risk detection, recommendations, and automated reporting",
        ],
    },
    {
        "title": "Problem Statement",
        "bullets": [
            "Social performance data is fragmented across multiple platforms",
            "Creators and brands struggle to understand audience mood, moderation risk, and growth direction quickly",
            "Manual reporting is slow and difficult to repeat consistently",
        ],
    },
    {
        "title": "Project Objective",
        "bullets": [
            "Bring Instagram, YouTube, and X / Twitter data into one analytics workspace",
            "Use AI-style analysis for sentiment, emotion, toxicity, prediction, and explainability",
            "Provide a simple dashboard for both end users and administrators",
        ],
    },
    {
        "title": "System Architecture",
        "bullets": [
            "Frontend: React + Vite + Tailwind + Recharts",
            "Backend: FastAPI services for auth, providers, dashboard, alerts, and reports",
            "Storage: MongoDB for data, Redis / Memurai for connected preview + dashboard snapshot cache, local storage for uploads and HTML reports",
            "Integrations: Firebase, Google APIs, Meta APIs, and an X / Twitter live source",
        ],
    },
    {
        "title": "Implemented User Features",
        "bullets": [
            "Real-time dashboard metrics and platform rollups",
            "Sentiment analysis, emotion detection, and toxicity detection",
            "Audience insights, predictive analysis, explainable AI, and floating analytics assistant",
            "Trending hashtags, recommendations, crisis alerts, and automated reports",
        ],
    },
    {
        "title": "Implemented Admin Features",
        "bullets": [
            "Managed user monitoring and editing",
            "User-specific analytics inspection",
            "Connection and report removal",
            "System alert creation and operations overview",
        ],
    },
    {
        "title": "Analytics Engine",
        "bullets": [
            "Content score combines views, likes, comments, replies, reposts, quotes, saves, and shares",
            "Trend strength is grouped by day of week and publishing window",
            "Prediction compares recent engagement against earlier baseline momentum",
            "Explainable AI exposes the factors behind audience, risk, and recommendation outputs",
        ],
    },
    {
        "title": "Platform Connection Flow",
        "bullets": [
            "Instagram: Professional account + Facebook Page + Meta app permissions",
            "YouTube: Google OAuth + YouTube Data API + YouTube Analytics API",
            "X / Twitter: Handle-based connect using a live public data source token",
            "Connected data is cached and aggregated into dashboard snapshots for faster reloads",
        ],
    },
    {
        "title": "Setup Requirements",
        "bullets": [
            "Windows machine with Node.js, Python 3.11, MongoDB, Redis or Memurai, and Git",
            "Firebase project with Email, Google, GitHub, and Facebook providers enabled",
            "Google and Meta developer credentials configured in environment files",
            "One X / Twitter live source token configured in backend .env",
        ],
    },
    {
        "title": "Project Deliverables",
        "bullets": [
            "Full-stack source code with separate frontend and backend",
            "Single README handoff guide with setup, workflow, analytics formulas, and file guide",
            "Shareable HTML report generation",
            "Production frontend build and backend compile verification completed",
        ],
    },
    {
        "title": "Future Scope",
        "bullets": [
            "Replace heuristic NLP fallback with hosted transformer models",
            "Add scheduled background sync jobs and email alerts",
            "Add richer audience segmentation and cross-platform campaign attribution",
            "Deploy to cloud infrastructure with role-based monitoring and audit logs",
        ],
    },
    {
        "title": "Conclusion",
        "bullets": [
            "Synapse centralizes social analytics, moderation signals, prediction, and reporting in one system",
            "The current build is demo-ready, client-ready, and documented for local Windows setup",
            "It satisfies the requested feature set for an academic final-year AI social media analytics project",
        ],
    },
]


def pxml(text: str) -> str:
    return dedent(text).strip()


def content_types_xml(slide_count: int) -> str:
    slide_overrides = "\n".join(
        f'  <Override PartName="/ppt/slides/slide{index}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
        for index in range(1, slide_count + 1)
    )
    return pxml(
        f"""
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
          <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
          <Default Extension="xml" ContentType="application/xml"/>
          <Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
          <Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>
          <Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>
          <Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>
          <Override PartName="/ppt/presProps.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presProps+xml"/>
          <Override PartName="/ppt/viewProps.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.viewProps+xml"/>
          <Override PartName="/ppt/tableStyles.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.tableStyles+xml"/>
          <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
          <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
        {slide_overrides}
        </Types>
        """
    )


ROOT_RELS_XML = pxml(
    """
    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
      <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
      <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
      <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
    </Relationships>
    """
)


APP_XML = pxml(
    """
    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
      xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
      <Application>OpenAI Codex</Application>
      <PresentationFormat>On-screen Show (16:9)</PresentationFormat>
      <Slides>12</Slides>
      <Notes>0</Notes>
      <HiddenSlides>0</HiddenSlides>
      <MMClips>0</MMClips>
      <ScaleCrop>false</ScaleCrop>
      <HeadingPairs>
        <vt:vector size="2" baseType="variant">
          <vt:variant><vt:lpstr>Theme</vt:lpstr></vt:variant>
          <vt:variant><vt:i4>1</vt:i4></vt:variant>
        </vt:vector>
      </HeadingPairs>
      <TitlesOfParts>
        <vt:vector size="1" baseType="lpstr">
          <vt:lpstr>Office Theme</vt:lpstr>
        </vt:vector>
      </TitlesOfParts>
      <Company>OpenAI</Company>
      <LinksUpToDate>false</LinksUpToDate>
      <SharedDoc>false</SharedDoc>
      <HyperlinksChanged>false</HyperlinksChanged>
      <AppVersion>1.0</AppVersion>
    </Properties>
    """
)


def core_xml() -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return pxml(
        f"""
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
            xmlns:dc="http://purl.org/dc/elements/1.1/"
            xmlns:dcterms="http://purl.org/dc/terms/"
            xmlns:dcmitype="http://purl.org/dc/dcmitype/"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
          <dc:title>Synapse AI Social Media Analytics</dc:title>
          <dc:creator>OpenAI Codex</dc:creator>
          <cp:lastModifiedBy>OpenAI Codex</cp:lastModifiedBy>
          <dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created>
          <dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified>
        </cp:coreProperties>
        """
    )


def presentation_xml(slide_count: int) -> str:
    slide_ids = "\n".join(
        f'    <p:sldId id="{255 + index}" r:id="rId{index + 1}"/>'
        for index in range(1, slide_count + 1)
    )
    return pxml(
        f"""
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
            xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
            xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
          <p:sldMasterIdLst>
            <p:sldMasterId id="2147483648" r:id="rId{slide_count + 1}"/>
          </p:sldMasterIdLst>
          <p:sldIdLst>
        {slide_ids}
          </p:sldIdLst>
          <p:sldSz cx="12192000" cy="6858000"/>
          <p:notesSz cx="6858000" cy="9144000"/>
          <p:defaultTextStyle/>
        </p:presentation>
        """
    )


def presentation_rels_xml(slide_count: int) -> str:
    slide_rels = "\n".join(
        f'  <Relationship Id="rId{index}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide{index}.xml"/>'
        for index in range(1, slide_count + 1)
    )
    master_id = slide_count + 1
    return pxml(
        f"""
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
        {slide_rels}
          <Relationship Id="rId{master_id}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>
          <Relationship Id="rId{master_id + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/presProps" Target="presProps.xml"/>
          <Relationship Id="rId{master_id + 2}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/viewProps" Target="viewProps.xml"/>
          <Relationship Id="rId{master_id + 3}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/tableStyles" Target="tableStyles.xml"/>
        </Relationships>
        """
    )


PRES_PROPS_XML = pxml(
    """
    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <p:presentationPr xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
        xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
        xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"/>
    """
)


VIEW_PROPS_XML = pxml(
    """
    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <p:viewPr xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
        xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
        xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
      <p:normalViewPr>
        <p:restoredLeft sz="15620"/>
        <p:restoredTop sz="94660"/>
      </p:normalViewPr>
      <p:slideViewPr>
        <p:cSldViewPr snapToGrid="1" snapToObjects="1"/>
      </p:slideViewPr>
      <p:notesTextViewPr>
        <p:cViewPr varScale="1"/>
      </p:notesTextViewPr>
    </p:viewPr>
    """
)


TABLE_STYLES_XML = pxml(
    """
    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <a:tblStyleLst xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" def="{5C22544A-7EE6-4342-B048-85BDC9FD1C3A}"/>
    """
)


THEME_XML = pxml(
    """
    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="Synapse Theme">
      <a:themeElements>
        <a:clrScheme name="Synapse Colors">
          <a:dk1><a:srgbClr val="0B1120"/></a:dk1>
          <a:lt1><a:srgbClr val="F8FAFC"/></a:lt1>
          <a:dk2><a:srgbClr val="111827"/></a:dk2>
          <a:lt2><a:srgbClr val="E2E8F0"/></a:lt2>
          <a:accent1><a:srgbClr val="00E5FF"/></a:accent1>
          <a:accent2><a:srgbClr val="F43F5E"/></a:accent2>
          <a:accent3><a:srgbClr val="F59E0B"/></a:accent3>
          <a:accent4><a:srgbClr val="22C55E"/></a:accent4>
          <a:accent5><a:srgbClr val="A855F7"/></a:accent5>
          <a:accent6><a:srgbClr val="94A3B8"/></a:accent6>
          <a:hlink><a:srgbClr val="38BDF8"/></a:hlink>
          <a:folHlink><a:srgbClr val="7C3AED"/></a:folHlink>
        </a:clrScheme>
        <a:fontScheme name="Synapse Fonts">
          <a:majorFont>
            <a:latin typeface="Aptos Display"/>
            <a:ea typeface=""/>
            <a:cs typeface=""/>
          </a:majorFont>
          <a:minorFont>
            <a:latin typeface="Aptos"/>
            <a:ea typeface=""/>
            <a:cs typeface=""/>
          </a:minorFont>
        </a:fontScheme>
        <a:fmtScheme name="Synapse Format">
          <a:fillStyleLst>
            <a:solidFill><a:schemeClr val="accent1"/></a:solidFill>
            <a:solidFill><a:schemeClr val="accent2"/></a:solidFill>
            <a:solidFill><a:schemeClr val="accent3"/></a:solidFill>
          </a:fillStyleLst>
          <a:lnStyleLst>
            <a:ln w="9525"><a:solidFill><a:schemeClr val="accent1"/></a:solidFill></a:ln>
            <a:ln w="25400"><a:solidFill><a:schemeClr val="accent2"/></a:solidFill></a:ln>
            <a:ln w="38100"><a:solidFill><a:schemeClr val="accent3"/></a:solidFill></a:ln>
          </a:lnStyleLst>
          <a:effectStyleLst>
            <a:effectStyle><a:effectLst/></a:effectStyle>
            <a:effectStyle><a:effectLst/></a:effectStyle>
            <a:effectStyle><a:effectLst/></a:effectStyle>
          </a:effectStyleLst>
          <a:bgFillStyleLst>
            <a:solidFill><a:schemeClr val="dk1"/></a:solidFill>
            <a:solidFill><a:schemeClr val="dk2"/></a:solidFill>
            <a:solidFill><a:schemeClr val="lt1"/></a:solidFill>
          </a:bgFillStyleLst>
        </a:fmtScheme>
      </a:themeElements>
      <a:objectDefaults/>
      <a:extraClrSchemeLst/>
    </a:theme>
    """
)


SLIDE_MASTER_XML = pxml(
    """
    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
        xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
        xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
      <p:cSld name="Synapse Master">
        <p:spTree>
          <p:nvGrpSpPr>
            <p:cNvPr id="1" name=""/>
            <p:cNvGrpSpPr/>
            <p:nvPr/>
          </p:nvGrpSpPr>
          <p:grpSpPr>
            <a:xfrm>
              <a:off x="0" y="0"/>
              <a:ext cx="0" cy="0"/>
              <a:chOff x="0" y="0"/>
              <a:chExt cx="0" cy="0"/>
            </a:xfrm>
          </p:grpSpPr>
        </p:spTree>
      </p:cSld>
      <p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/>
      <p:sldLayoutIdLst>
        <p:sldLayoutId id="2147483649" r:id="rId1"/>
      </p:sldLayoutIdLst>
      <p:txStyles>
        <p:titleStyle/>
        <p:bodyStyle/>
        <p:otherStyle/>
      </p:txStyles>
    </p:sldMaster>
    """
)


SLIDE_MASTER_RELS_XML = pxml(
    """
    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
      <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
      <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="../theme/theme1.xml"/>
    </Relationships>
    """
)


SLIDE_LAYOUT_XML = pxml(
    """
    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
        xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
        xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
        type="blank" preserve="1">
      <p:cSld name="Blank">
        <p:spTree>
          <p:nvGrpSpPr>
            <p:cNvPr id="1" name=""/>
            <p:cNvGrpSpPr/>
            <p:nvPr/>
          </p:nvGrpSpPr>
          <p:grpSpPr>
            <a:xfrm>
              <a:off x="0" y="0"/>
              <a:ext cx="0" cy="0"/>
              <a:chOff x="0" y="0"/>
              <a:chExt cx="0" cy="0"/>
            </a:xfrm>
          </p:grpSpPr>
        </p:spTree>
      </p:cSld>
      <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
    </p:sldLayout>
    """
)


SLIDE_LAYOUT_RELS_XML = pxml(
    """
    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
      <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="../slideMasters/slideMaster1.xml"/>
    </Relationships>
    """
)


def text_box_xml(shape_id: int, name: str, x: int, y: int, cx: int, cy: int, paragraphs: list[tuple[str, int, bool]]) -> str:
    paragraph_xml = []
    for text, size, bold in paragraphs:
        escaped = escape(text)
        bold_attr = ' b="1"' if bold else ""
        paragraph_xml.append(
            f"""
            <a:p>
              <a:r>
                <a:rPr lang="en-US" sz="{size}"{bold_attr}/>
                <a:t>{escaped}</a:t>
              </a:r>
              <a:endParaRPr lang="en-US" sz="{size}"/>
            </a:p>
            """
        )

    return pxml(
        f"""
        <p:sp>
          <p:nvSpPr>
            <p:cNvPr id="{shape_id}" name="{escape(name)}"/>
            <p:cNvSpPr txBox="1"/>
            <p:nvPr/>
          </p:nvSpPr>
          <p:spPr>
            <a:xfrm>
              <a:off x="{x}" y="{y}"/>
              <a:ext cx="{cx}" cy="{cy}"/>
            </a:xfrm>
            <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
            <a:noFill/>
            <a:ln><a:noFill/></a:ln>
          </p:spPr>
          <p:txBody>
            <a:bodyPr wrap="square" lIns="91440" tIns="45720" rIns="91440" bIns="45720"/>
            <a:lstStyle/>
            {''.join(paragraph_xml)}
          </p:txBody>
        </p:sp>
        """
    )


def accent_bar_xml(shape_id: int) -> str:
    return pxml(
        f"""
        <p:sp>
          <p:nvSpPr>
            <p:cNvPr id="{shape_id}" name="Accent Bar"/>
            <p:cNvSpPr/>
            <p:nvPr/>
          </p:nvSpPr>
          <p:spPr>
            <a:xfrm>
              <a:off x="457200" y="342900"/>
              <a:ext cx="10972800" cy="228600"/>
            </a:xfrm>
            <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
            <a:solidFill><a:srgbClr val="00E5FF"/></a:solidFill>
            <a:ln><a:noFill/></a:ln>
          </p:spPr>
        </p:sp>
        """
    )


def slide_xml(title: str, bullets: list[str], subtitle: str | None = None) -> str:
    body_lines = []
    if subtitle:
        body_lines.append((subtitle, 2200, False))
        body_lines.append(("", 1000, False))
    body_lines.extend([(f"- {bullet}", 2000, False) for bullet in bullets])
    body_lines = [item for item in body_lines if item[0] != "" or item[1] != 1000]

    shapes = [
        accent_bar_xml(2),
        text_box_xml(3, "Title", 685800, 731520, 10744200, 914400, [(title, 2800, True)]),
        text_box_xml(4, "Body", 685800, 1645920, 10744200, 4389120, body_lines),
    ]
    return pxml(
        f"""
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
            xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
            xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
          <p:cSld>
            <p:spTree>
              <p:nvGrpSpPr>
                <p:cNvPr id="1" name=""/>
                <p:cNvGrpSpPr/>
                <p:nvPr/>
              </p:nvGrpSpPr>
              <p:grpSpPr>
                <a:xfrm>
                  <a:off x="0" y="0"/>
                  <a:ext cx="0" cy="0"/>
                  <a:chOff x="0" y="0"/>
                  <a:chExt cx="0" cy="0"/>
                </a:xfrm>
              </p:grpSpPr>
              {''.join(shapes)}
            </p:spTree>
          </p:cSld>
          <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
        </p:sld>
        """
    )


SLIDE_RELS_XML = pxml(
    """
    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
      <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
    </Relationships>
    """
)


def build_presentation() -> None:
    with ZipFile(OUTPUT, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types_xml(len(SLIDES)))
        archive.writestr("_rels/.rels", ROOT_RELS_XML)
        archive.writestr("docProps/app.xml", APP_XML)
        archive.writestr("docProps/core.xml", core_xml())
        archive.writestr("ppt/presentation.xml", presentation_xml(len(SLIDES)))
        archive.writestr("ppt/_rels/presentation.xml.rels", presentation_rels_xml(len(SLIDES)))
        archive.writestr("ppt/presProps.xml", PRES_PROPS_XML)
        archive.writestr("ppt/viewProps.xml", VIEW_PROPS_XML)
        archive.writestr("ppt/tableStyles.xml", TABLE_STYLES_XML)
        archive.writestr("ppt/theme/theme1.xml", THEME_XML)
        archive.writestr("ppt/slideMasters/slideMaster1.xml", SLIDE_MASTER_XML)
        archive.writestr("ppt/slideMasters/_rels/slideMaster1.xml.rels", SLIDE_MASTER_RELS_XML)
        archive.writestr("ppt/slideLayouts/slideLayout1.xml", SLIDE_LAYOUT_XML)
        archive.writestr("ppt/slideLayouts/_rels/slideLayout1.xml.rels", SLIDE_LAYOUT_RELS_XML)

        for index, slide in enumerate(SLIDES, start=1):
            archive.writestr(
                f"ppt/slides/slide{index}.xml",
                slide_xml(slide["title"], slide["bullets"], slide.get("subtitle")),
            )
            archive.writestr(f"ppt/slides/_rels/slide{index}.xml.rels", SLIDE_RELS_XML)


if __name__ == "__main__":
    build_presentation()
    print(f"Created: {OUTPUT}")
