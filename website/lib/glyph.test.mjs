// node --test — the codec port against fixtures the Python codec produced.
//
// Every expected value below came out of projects/glyph/models/glyph-nanogpt-1/
// codec.py (decode_glyph + glyph_to_svg_path + the GlyphSyntaxError messages)
// run over real lines from projects/glyph/test/<letter>.txt plus a set of
// hand-built grammar cases, so the port is checked byte for byte. To
// regenerate: decode the same lines with the Python codec and paste.

import { test } from "node:test";
import assert from "node:assert/strict";
import {
  ALPHABET,
  COORDS,
  BOUNDARY_ID,
  N_BUCKETS,
  unbucket,
  isCoord,
  decodeGlyph,
  decodeGlyphPartial,
  glyphToSvgPath,
  contourToSvgPath,
  glyphToPathCommands,
  drawGlyphOn,
  glyphBounds,
  layoutWord,
  fontMetrics,
  windForNonzero,
  reverseContour,
  SPACE_ADVANCE,
  MISSING_ADVANCE,
  GlyphSyntaxError,
} from "./glyph.js";

// Python-produced. Do not edit by hand.
const PY = {"coords":"⠀⠁⠂⠃⠄⠅⠆⠇⠈⠉⠊⠋⠌⠍⠎⠏⠐⠑⠒⠓⠔⠕⠖⠗⠘⠙⠚⠛⠜⠝⠞⠟⠠⠡⠢⠣⠤⠥⠦⠧⠨⠩⠪⠫⠬⠭⠮⠯⠰⠱⠲⠳⠴⠵⠶⠷⠸⠹⠺⠻⠼⠽⠾⠿⡀⡁⡂⡃⡄⡅⡆⡇⡈⡉⡊⡋⡌⡍⡎⡏⡐⡑⡒⡓⡔⡕⡖⡗⡘⡙⡚⡛⡜⡝⡞⡟","alphabet":"abcdefghijklmnopqrstuvwxyzMLQZ⠀⠁⠂⠃⠄⠅⠆⠇⠈⠉⠊⠋⠌⠍⠎⠏⠐⠑⠒⠓⠔⠕⠖⠗⠘⠙⠚⠛⠜⠝⠞⠟⠠⠡⠢⠣⠤⠥⠦⠧⠨⠩⠪⠫⠬⠭⠮⠯⠰⠱⠲⠳⠴⠵⠶⠷⠸⠹⠺⠻⠼⠽⠾⠿⡀⡁⡂⡃⡄⡅⡆⡇⡈⡉⡊⡋⡌⡍⡎⡏⡐⡑⡒⡓⡔⡕⡖⡗⡘⡙⡚⡛⡜⡝⡞⡟\n","unbucket":[-512,-496,-480,-464,-448,-432,-416,-400,-384,-368,-352,-336,-320,-304,-288,-272,-256,-240,-224,-208,-192,-176,-160,-144,-128,-112,-96,-80,-64,-48,-32,-16,0,16,32,48,64,80,96,112,128,144,160,176,192,208,224,240,256,272,288,304,320,336,352,368,384,400,416,432,448,464,480,496,512,528,544,560,576,592,608,624,640,656,672,688,704,720,736,752,768,784,800,816,832,848,864,880,896,912,928,944,960,976,992,1008],"fixtures":[{"line":"s⠼M⠮⠠Q⠫⠠⠧⠡Q⠤⠢⠢⠥L⠣⠦Q⠥⠤⠨⠣Q⠫⠢⠮⠢Q⠱⠢⠲⠣Q⠴⠣⠶⠥Q⠷⠦⠷⠨Q⠷⠫⠶⠬Q⠴⠮⠲⠮Q⠰⠯⠭⠰Q⠫⠱⠩⠲Q⠦⠳⠥⠴Q⠤⠶⠤⠹Q⠤⠼⠥⠾Q⠧⡀⠩⡀Q⠬⡁⠯⡁Q⠱⡁⠴⡁Q⠶⡀⠸⠿L⠷⠽Q⠵⠾⠳⠾Q⠱⠿⠮⠿Q⠫⠿⠩⠾Q⠦⠼⠦⠹Q⠦⠷⠨⠶Q⠩⠴⠫⠴Q⠭⠳⠰⠲Q⠲⠱⠵⠰Q⠷⠯⠸⠮Q⠺⠬⠺⠩Q⠺⠦⠸⠤Q⠶⠢⠴⠡Q⠱⠠⠮⠠Z","decoded":{"letter":"s","adv":448,"contours":[[["M",[224,0]],["Q",[176,0],[112,16]],["Q",[64,32],[32,80]],["L",[48,96]],["Q",[80,64],[128,48]],["Q",[176,32],[224,32]],["Q",[272,32],[288,48]],["Q",[320,48],[352,80]],["Q",[368,96],[368,128]],["Q",[368,176],[352,192]],["Q",[320,224],[288,224]],["Q",[256,240],[208,256]],["Q",[176,272],[144,288]],["Q",[96,304],[80,320]],["Q",[64,352],[64,400]],["Q",[64,448],[80,480]],["Q",[112,512],[144,512]],["Q",[192,528],[240,528]],["Q",[272,528],[320,528]],["Q",[352,512],[384,496]],["L",[368,464]],["Q",[336,480],[304,480]],["Q",[272,496],[224,496]],["Q",[176,496],[144,480]],["Q",[96,448],[96,400]],["Q",[96,368],[128,352]],["Q",[144,320],[176,320]],["Q",[208,304],[256,288]],["Q",[288,272],[336,256]],["Q",[368,240],[384,224]],["Q",[416,192],[416,144]],["Q",[416,96],[384,64]],["Q",[352,32],[320,16]],["Q",[272,0],[224,0]]]]},"path":"M224 0Q176 0 112 16Q64 32 32 80L48 96Q80 64 128 48Q176 32 224 32Q272 32 288 48Q320 48 352 80Q368 96 368 128Q368 176 352 192Q320 224 288 224Q256 240 208 256Q176 272 144 288Q96 304 80 320Q64 352 64 400Q64 448 80 480Q112 512 144 512Q192 528 240 528Q272 528 320 528Q352 512 384 496L368 464Q336 480 304 480Q272 496 224 496Q176 496 144 480Q96 448 96 400Q96 368 128 352Q144 320 176 320Q208 304 256 288Q288 272 336 256Q368 240 384 224Q416 192 416 144Q416 96 384 64Q352 32 320 16Q272 0 224 0Z"},{"line":"s⠼M⠮⠟Q⠪⠟⠧⠠Q⠤⠠⠢⠡L⠢⠫Q⠧⠪⠩⠪Q⠫⠪⠭⠪Q⠯⠪⠰⠪Q⠰⠪⠰⠪Q⠰⠫⠰⠫Q⠰⠫⠯⠫L⠨⠬Q⠤⠬⠢⠮Q⠡⠱⠡⠵Q⠡⠻⠤⠾Q⠨⡀⠯⡀Q⠲⡀⠵⡀Q⠸⡀⠺⡀L⠺⠵Q⠷⠶⠴⠶Q⠲⠶⠰⠶L⠰⠶Q⠮⠶⠮⠶Q⠭⠶⠭⠶Q⠭⠵⠭⠵Q⠭⠵⠮⠵L⠴⠴Q⠹⠴⠺⠲Q⠼⠰⠼⠫Q⠼⠥⠹⠢Q⠵⠟⠮⠟Z","decoded":{"letter":"s","adv":448,"contours":[[["M",[224,-16]],["Q",[160,-16],[112,0]],["Q",[64,0],[32,16]],["L",[32,176]],["Q",[112,160],[144,160]],["Q",[176,160],[208,160]],["Q",[240,160],[256,160]],["Q",[256,160],[256,160]],["Q",[256,176],[256,176]],["Q",[256,176],[240,176]],["L",[128,192]],["Q",[64,192],[32,224]],["Q",[16,272],[16,336]],["Q",[16,432],[64,480]],["Q",[128,512],[240,512]],["Q",[288,512],[336,512]],["Q",[384,512],[416,512]],["L",[416,336]],["Q",[368,352],[320,352]],["Q",[288,352],[256,352]],["L",[256,352]],["Q",[224,352],[224,352]],["Q",[208,352],[208,352]],["Q",[208,336],[208,336]],["Q",[208,336],[224,336]],["L",[320,320]],["Q",[400,320],[416,288]],["Q",[448,256],[448,176]],["Q",[448,80],[400,32]],["Q",[336,-16],[224,-16]]]]},"path":"M224 -16Q160 -16 112 0Q64 0 32 16L32 176Q112 160 144 160Q176 160 208 160Q240 160 256 160Q256 160 256 160Q256 176 256 176Q256 176 240 176L128 192Q64 192 32 224Q16 272 16 336Q16 432 64 480Q128 512 240 512Q288 512 336 512Q384 512 416 512L416 336Q368 352 320 352Q288 352 256 352L256 352Q224 352 224 352Q208 352 208 352Q208 336 208 336Q208 336 224 336L320 320Q400 320 416 288Q448 256 448 176Q448 80 400 32Q336 -16 224 -16Z"},{"line":"u⡆M⠱⠟Q⠫⠟⠨⠣Q⠥⠦⠥⠭L⠥⠭L⠥⡁L⠬⡁L⠬⠭Q⠬⠨⠭⠦Q⠮⠤⠲⠤Q⠷⠤⠺⠦L⠺⡁L⡁⡁L⡁⠦L⡂⠟L⠿⠟Q⠾⠟⠽⠠Q⠽⠠⠼⠡L⠻⠣L⠺⠣Q⠸⠡⠶⠠Q⠴⠟⠱⠟Z","decoded":{"letter":"u","adv":608,"contours":[[["M",[272,-16]],["Q",[176,-16],[128,48]],["Q",[80,96],[80,208]],["L",[80,208]],["L",[80,528]],["L",[192,528]],["L",[192,208]],["Q",[192,128],[208,96]],["Q",[224,64],[288,64]],["Q",[368,64],[416,96]],["L",[416,528]],["L",[528,528]],["L",[528,96]],["L",[544,-16]],["L",[496,-16]],["Q",[480,-16],[464,0]],["Q",[464,0],[448,16]],["L",[432,48]],["L",[416,48]],["Q",[384,16],[352,0]],["Q",[320,-16],[272,-16]]]]},"path":"M272 -16Q176 -16 128 48Q80 96 80 208L80 208L80 528L192 528L192 208Q192 128 208 96Q224 64 288 64Q368 64 416 96L416 528L528 528L528 96L544 -16L496 -16Q480 -16 464 0Q464 0 448 16L432 48L416 48Q384 16 352 0Q320 -16 272 -16Z"},{"line":"u⡆M⠰⠟Q⠪⠟⠧⠣Q⠤⠦⠤⠭L⠤⡂L⠫⡂L⠫⠮Q⠫⠪⠭⠨Q⠯⠥⠳⠥Q⠵⠥⠷⠧Q⠹⠨⠺⠪Q⠻⠬⠻⠮L⠻⡂L⡂⡂L⡂⠠L⠻⠠L⠻⠦Q⠺⠣⠷⠡Q⠴⠟⠰⠟Z","decoded":{"letter":"u","adv":608,"contours":[[["M",[256,-16]],["Q",[160,-16],[112,48]],["Q",[64,96],[64,208]],["L",[64,544]],["L",[176,544]],["L",[176,224]],["Q",[176,160],[208,128]],["Q",[240,80],[304,80]],["Q",[336,80],[368,112]],["Q",[400,128],[416,160]],["Q",[432,192],[432,224]],["L",[432,544]],["L",[544,544]],["L",[544,0]],["L",[432,0]],["L",[432,96]],["Q",[416,48],[368,16]],["Q",[320,-16],[256,-16]]]]},"path":"M256 -16Q160 -16 112 48Q64 96 64 208L64 544L176 544L176 224Q176 160 208 128Q240 80 304 80Q336 80 368 112Q400 128 416 160Q432 192 432 224L432 544L544 544L544 0L432 0L432 96Q416 48 368 16Q320 -16 256 -16Z"},{"line":"p⡃M⠥⠖L⠥⡀L⠦⡀L⠧⠽Q⠩⠾⠬⠿Q⠯⡀⠲⡀Q⠹⡀⠼⠼Q⠿⠹⠿⠰Q⠿⠧⠻⠣Q⠸⠠⠰⠠Q⠭⠠⠫⠠Q⠩⠠⠧⠡L⠧⠖ZM⠫⠡Q⠩⠢⠧⠢L⠧⠻Q⠩⠽⠬⠾Q⠯⠿⠲⠿L⠲⠿Q⠸⠿⠻⠼Q⠾⠸⠾⠰Q⠾⠨⠻⠤Q⠸⠡⠰⠡Q⠭⠡⠫⠡Z","decoded":{"letter":"p","adv":560,"contours":[[["M",[80,-160]],["L",[80,512]],["L",[96,512]],["L",[112,464]],["Q",[144,480],[192,496]],["Q",[240,512],[288,512]],["Q",[400,512],[448,448]],["Q",[496,400],[496,256]],["Q",[496,112],[432,48]],["Q",[384,0],[256,0]],["Q",[208,0],[176,0]],["Q",[144,0],[112,16]],["L",[112,-160]]],[["M",[176,16]],["Q",[144,32],[112,32]],["L",[112,432]],["Q",[144,464],[192,480]],["Q",[240,496],[288,496]],["L",[288,496]],["Q",[384,496],[432,448]],["Q",[480,384],[480,256]],["Q",[480,128],[432,64]],["Q",[384,16],[256,16]],["Q",[208,16],[176,16]]]]},"path":"M80 -160L80 512L96 512L112 464Q144 480 192 496Q240 512 288 512Q400 512 448 448Q496 400 496 256Q496 112 432 48Q384 0 256 0Q208 0 176 0Q144 0 112 16L112 -160ZM176 16Q144 32 112 32L112 432Q144 464 192 480Q240 496 288 496L288 496Q384 496 432 448Q480 384 480 256Q480 128 432 64Q384 16 256 16Q208 16 176 16Z"},{"line":"p⡋M⠧⠔L⠧⡁L⠩⡁L⠩⠷Q⠩⠸⠩⠹Q⠬⠽⠯⠿Q⠳⡁⠷⡁L⠷⡁Q⠼⡁⡀⠿Q⡃⠽⡅⠹Q⡇⠵⡇⠱Q⡇⠬⡅⠨Q⡃⠤⡀⠢Q⠼⠠⠷⠠Q⠳⠠⠯⠢Q⠬⠤⠩⠨Q⠩⠩⠩⠪L⠩⠔ZM⠷⠡Q⠳⠡⠰⠣Q⠬⠥⠫⠩Q⠩⠬⠩⠱Q⠩⠵⠫⠸Q⠬⠼⠰⠾Q⠳⡀⠷⡀L⠷⡀Q⠼⡀⠿⠾Q⡂⠼⡄⠸Q⡆⠵⡆⠱Q⡆⠬⡄⠩Q⡂⠥⠿⠣Q⠼⠡⠷⠡Z","decoded":{"letter":"p","adv":688,"contours":[[["M",[112,-192]],["L",[112,528]],["L",[144,528]],["L",[144,368]],["Q",[144,384],[144,400]],["Q",[192,464],[240,496]],["Q",[304,528],[368,528]],["L",[368,528]],["Q",[448,528],[512,496]],["Q",[560,464],[592,400]],["Q",[624,336],[624,272]],["Q",[624,192],[592,128]],["Q",[560,64],[512,32]],["Q",[448,0],[368,0]],["Q",[304,0],[240,32]],["Q",[192,64],[144,128]],["Q",[144,144],[144,160]],["L",[144,-192]]],[["M",[368,16]],["Q",[304,16],[256,48]],["Q",[192,80],[176,144]],["Q",[144,192],[144,272]],["Q",[144,336],[176,384]],["Q",[192,448],[256,480]],["Q",[304,512],[368,512]],["L",[368,512]],["Q",[448,512],[496,480]],["Q",[544,448],[576,384]],["Q",[608,336],[608,272]],["Q",[608,192],[576,144]],["Q",[544,80],[496,48]],["Q",[448,16],[368,16]]]]},"path":"M112 -192L112 528L144 528L144 368Q144 384 144 400Q192 464 240 496Q304 528 368 528L368 528Q448 528 512 496Q560 464 592 400Q624 336 624 272Q624 192 592 128Q560 64 512 32Q448 0 368 0Q304 0 240 32Q192 64 144 128Q144 144 144 160L144 -192ZM368 16Q304 16 256 48Q192 80 176 144Q144 192 144 272Q144 336 176 384Q192 448 256 480Q304 512 368 512L368 512Q448 512 496 480Q544 448 576 384Q608 336 608 272Q608 192 576 144Q544 80 496 48Q448 16 368 16Z"},{"line":"c⡄M⠴⠠Q⠯⠠⠫⠢Q⠧⠤⠥⠨Q⠣⠬⠣⠱L⠣⠱Q⠣⠶⠥⠺Q⠧⠽⠫⡀Q⠯⡂⠴⡂Q⠸⡂⠻⡀Q⠿⠿⡁⠼L⠾⠺Q⠽⠼⠺⠾Q⠷⠿⠴⠿Q⠰⠿⠭⠽Q⠪⠻⠨⠸Q⠦⠵⠦⠱Q⠦⠭⠨⠩Q⠪⠦⠭⠤Q⠰⠣⠴⠣Q⠷⠣⠺⠤Q⠽⠥⠾⠨L⡁⠦Q⠿⠣⠻⠡Q⠸⠠⠴⠠Z","decoded":{"letter":"c","adv":576,"contours":[[["M",[320,0]],["Q",[240,0],[176,32]],["Q",[112,64],[80,128]],["Q",[48,192],[48,272]],["L",[48,272]],["Q",[48,352],[80,416]],["Q",[112,464],[176,512]],["Q",[240,544],[320,544]],["Q",[384,544],[432,512]],["Q",[496,496],[528,448]],["L",[480,416]],["Q",[464,448],[416,480]],["Q",[368,496],[320,496]],["Q",[256,496],[208,464]],["Q",[160,432],[128,384]],["Q",[96,336],[96,272]],["Q",[96,208],[128,144]],["Q",[160,96],[208,64]],["Q",[256,48],[320,48]],["Q",[368,48],[416,64]],["Q",[464,80],[480,128]],["L",[528,96]],["Q",[496,48],[432,16]],["Q",[384,0],[320,0]]]]},"path":"M320 0Q240 0 176 32Q112 64 80 128Q48 192 48 272L48 272Q48 352 80 416Q112 464 176 512Q240 544 320 544Q384 544 432 512Q496 496 528 448L480 416Q464 448 416 480Q368 496 320 496Q256 496 208 464Q160 432 128 384Q96 336 96 272Q96 208 128 144Q160 96 208 64Q256 48 320 48Q368 48 416 64Q464 80 480 128L528 96Q496 48 432 16Q384 0 320 0Z"},{"line":"o⡈M⠳⠟Q⠮⠟⠫⠡Q⠧⠣⠥⠧Q⠢⠪⠢⠯Q⠢⠳⠥⠷Q⠧⠻⠫⠽Q⠯⠿⠴⠿Q⠹⠿⠽⠽Q⡁⠻⡃⠷Q⡅⠴⡅⠯Q⡅⠫⡃⠧Q⡁⠣⠽⠡Q⠹⠟⠳⠟ZM⠴⠧L⠴⠧Q⠲⠧⠱⠨Q⠰⠩⠰⠫Q⠯⠭⠯⠰Q⠯⠲⠯⠴Q⠰⠶⠱⠶Q⠲⠷⠴⠷Q⠵⠷⠶⠶Q⠸⠵⠸⠴Q⠹⠲⠹⠯Q⠹⠬⠸⠪Q⠸⠩⠷⠨Q⠶⠧⠴⠧Z","decoded":{"letter":"o","adv":640,"contours":[[["M",[304,-16]],["Q",[224,-16],[176,16]],["Q",[112,48],[80,112]],["Q",[32,160],[32,240]],["Q",[32,304],[80,368]],["Q",[112,432],[176,464]],["Q",[240,496],[320,496]],["Q",[400,496],[464,464]],["Q",[528,432],[560,368]],["Q",[592,320],[592,240]],["Q",[592,176],[560,112]],["Q",[528,48],[464,16]],["Q",[400,-16],[304,-16]]],[["M",[320,112]],["L",[320,112]],["Q",[288,112],[272,128]],["Q",[256,144],[256,176]],["Q",[240,208],[240,256]],["Q",[240,288],[240,320]],["Q",[256,352],[272,352]],["Q",[288,368],[320,368]],["Q",[336,368],[352,352]],["Q",[384,336],[384,320]],["Q",[400,288],[400,240]],["Q",[400,192],[384,160]],["Q",[384,144],[368,128]],["Q",[352,112],[320,112]]]]},"path":"M304 -16Q224 -16 176 16Q112 48 80 112Q32 160 32 240Q32 304 80 368Q112 432 176 464Q240 496 320 496Q400 496 464 464Q528 432 560 368Q592 320 592 240Q592 176 560 112Q528 48 464 16Q400 -16 304 -16ZM320 112L320 112Q288 112 272 128Q256 144 256 176Q240 208 240 256Q240 288 240 320Q256 352 272 352Q288 368 320 368Q336 368 352 352Q384 336 384 320Q400 288 400 240Q400 192 384 160Q384 144 368 128Q352 112 320 112Z"},{"line":"m⡘M⠤⠠L⠤⡂L⠫⡂L⠫⠼Q⠬⠿⠯⡁Q⠱⡃⠵⡃Q⠹⡃⠻⡁Q⠾⠿⠾⠼Q⡀⠿⡃⡁Q⡅⡃⡉⡃Q⡎⡃⡑⠿Q⡔⠼⡔⠶L⡔⠠L⡍⠠L⡍⠴Q⡍⠹⡋⠻Q⡉⠼⡇⠼Q⡄⠼⡃⠻Q⡁⠺⡀⠸Q⡀⠷⡀⠴L⡀⠠L⠹⠠L⠹⠴Q⠹⠹⠷⠻Q⠵⠼⠲⠼Q⠰⠼⠯⠻Q⠭⠺⠬⠸Q⠬⠷⠬⠴L⠬⠠Z","decoded":{"letter":"m","adv":896,"contours":[[["M",[64,0]],["L",[64,544]],["L",[176,544]],["L",[176,448]],["Q",[192,496],[240,528]],["Q",[272,560],[336,560]],["Q",[400,560],[432,528]],["Q",[480,496],[480,448]],["Q",[512,496],[560,528]],["Q",[592,560],[656,560]],["Q",[736,560],[784,496]],["Q",[832,448],[832,352]],["L",[832,0]],["L",[720,0]],["L",[720,320]],["Q",[720,400],[688,432]],["Q",[656,448],[624,448]],["Q",[576,448],[560,432]],["Q",[528,416],[512,384]],["Q",[512,368],[512,320]],["L",[512,0]],["L",[400,0]],["L",[400,320]],["Q",[400,400],[368,432]],["Q",[336,448],[288,448]],["Q",[256,448],[240,432]],["Q",[208,416],[192,384]],["Q",[192,368],[192,320]],["L",[192,0]]]]},"path":"M64 0L64 544L176 544L176 448Q192 496 240 528Q272 560 336 560Q400 560 432 528Q480 496 480 448Q512 496 560 528Q592 560 656 560Q736 560 784 496Q832 448 832 352L832 0L720 0L720 320Q720 400 688 432Q656 448 624 448Q576 448 560 432Q528 416 512 384Q512 368 512 320L512 0L400 0L400 320Q400 400 368 432Q336 448 288 448Q256 448 240 432Q208 416 192 384Q192 368 192 320L192 0Z"},{"line":"t⠹M⠰⠠Q⠫⠠⠩⠢Q⠦⠥⠦⠩L⠦⡉L⠫⡉L⠫⡂L⠵⡂L⠵⠾L⠫⠾L⠫⠪Q⠫⠧⠬⠥Q⠮⠤⠰⠤Q⠳⠤⠵⠥L⠷⠢Q⠶⠡⠴⠠Q⠲⠠⠰⠠Z","decoded":{"letter":"t","adv":400,"contours":[[["M",[256,0]],["Q",[176,0],[144,32]],["Q",[96,80],[96,144]],["L",[96,656]],["L",[176,656]],["L",[176,544]],["L",[336,544]],["L",[336,480]],["L",[176,480]],["L",[176,160]],["Q",[176,112],[192,80]],["Q",[224,64],[256,64]],["Q",[304,64],[336,80]],["L",[368,32]],["Q",[352,16],[320,0]],["Q",[288,0],[256,0]]]]},"path":"M256 0Q176 0 144 32Q96 80 96 144L96 656L176 656L176 544L336 544L336 480L176 480L176 160Q176 112 192 80Q224 64 256 64Q304 64 336 80L368 32Q352 16 320 0Q288 0 256 0Z"},{"line":"e⠻M⠪⠟Q⠨⠟⠧⠡L⠤⠣Q⠣⠤⠣⠦L⠣⠹Q⠣⠺⠤⠼L⠧⠾Q⠨⠿⠪⠿L⠲⠿Q⠳⠿⠵⠾L⠷⠼Q⠸⠺⠸⠹L⠸⠮Q⠸⠫⠵⠫L⠵⠫L⠬⠫Q⠩⠫⠩⠩L⠩⠨Q⠩⠥⠬⠥L⠵⠥Q⠸⠥⠸⠣L⠸⠢Q⠸⠟⠵⠟ZM⠬⠰L⠬⠰Q⠩⠰⠩⠳L⠩⠷Q⠩⠹⠬⠹L⠰⠹Q⠲⠹⠲⠷L⠲⠳Q⠲⠰⠰⠰Z","decoded":{"letter":"e","adv":432,"contours":[[["M",[160,-16]],["Q",[128,-16],[112,16]],["L",[64,48]],["Q",[48,64],[48,96]],["L",[48,400]],["Q",[48,416],[64,448]],["L",[112,480]],["Q",[128,496],[160,496]],["L",[288,496]],["Q",[304,496],[336,480]],["L",[368,448]],["Q",[384,416],[384,400]],["L",[384,224]],["Q",[384,176],[336,176]],["L",[336,176]],["L",[192,176]],["Q",[144,176],[144,144]],["L",[144,128]],["Q",[144,80],[192,80]],["L",[336,80]],["Q",[384,80],[384,48]],["L",[384,32]],["Q",[384,-16],[336,-16]]],[["M",[192,256]],["L",[192,256]],["Q",[144,256],[144,304]],["L",[144,368]],["Q",[144,400],[192,400]],["L",[256,400]],["Q",[288,400],[288,368]],["L",[288,304]],["Q",[288,256],[256,256]]]]},"path":"M160 -16Q128 -16 112 16L64 48Q48 64 48 96L48 400Q48 416 64 448L112 480Q128 496 160 496L288 496Q304 496 336 480L368 448Q384 416 384 400L384 224Q384 176 336 176L336 176L192 176Q144 176 144 144L144 128Q144 80 192 80L336 80Q384 80 384 48L384 32Q384 -16 336 -16ZM192 256L192 256Q144 256 144 304L144 368Q144 400 192 400L256 400Q288 400 288 368L288 304Q288 256 256 256Z"},{"line":"r⠷M⠦⠠L⠦⠻L⠤⡂L⠧⡂Q⠨⡂⠩⡁Q⠩⡁⠪⡀L⠪⡀L⠫⠾L⠬⠾Q⠭⡀⠯⡁Q⠱⡂⠴⡂Q⠶⡂⠶⡂L⠶⠼L⠳⠼Q⠮⠼⠬⠺L⠬⠠Z","decoded":{"letter":"r","adv":368,"contours":[[["M",[96,0]],["L",[96,432]],["L",[64,544]],["L",[112,544]],["Q",[128,544],[144,528]],["Q",[144,528],[160,512]],["L",[160,512]],["L",[176,480]],["L",[192,480]],["Q",[208,512],[240,528]],["Q",[272,544],[320,544]],["Q",[352,544],[352,544]],["L",[352,448]],["L",[304,448]],["Q",[224,448],[192,416]],["L",[192,0]]]]},"path":"M96 0L96 432L64 544L112 544Q128 544 144 528Q144 528 160 512L160 512L176 480L192 480Q208 512 240 528Q272 544 320 544Q352 544 352 544L352 448L304 448Q224 448 192 416L192 0Z"},{"line":"j⠰M⠠⠖L⠟⠗Q⠢⠘⠣⠚Q⠥⠛⠦⠝Q⠧⠟⠧⠢L⠧⠾L⠩⠾L⠩⠢Q⠩⠠⠩⠞Q⠨⠜⠧⠚Q⠥⠘⠤⠗Q⠢⠖⠠⠖Z","decoded":{"letter":"j","adv":256,"contours":[[["M",[0,-160]],["L",[-16,-144]],["Q",[32,-128],[48,-96]],["Q",[80,-80],[96,-48]],["Q",[112,-16],[112,32]],["L",[112,480]],["L",[144,480]],["L",[144,32]],["Q",[144,0],[144,-32]],["Q",[128,-64],[112,-96]],["Q",[80,-128],[64,-144]],["Q",[32,-160],[0,-160]]]]},"path":"M0 -160L-16 -144Q32 -128 48 -96Q80 -80 96 -48Q112 -16 112 32L112 480L144 480L144 32Q144 0 144 -32Q128 -64 112 -96Q80 -128 64 -144Q32 -160 0 -160Z"},{"line":"g⡈M⠻⠔Q⠱⠔⠤⠖L⠤⠞Q⠱⠝⠷⠝Q⠸⠝⠹⠞Q⠹⠞⠹⠟L⠹⠣Q⠳⠡⠮⠡L⠬⠡Q⠨⠡⠥⠤Q⠣⠧⠣⠫L⠣⠸Q⠣⠼⠥⠿Q⠨⡂⠭⡂L⡄⡂L⡄⠞Q⡄⠚⡂⠗Q⠿⠔⠻⠔ZM⠰⠪Q⠯⠪⠮⠫Q⠮⠫⠮⠬L⠮⠷Q⠮⠹⠰⠹L⠹⠹L⠹⠫Q⠶⠪⠲⠪Z","decoded":{"letter":"g","adv":640,"contours":[[["M",[432,-192]],["Q",[272,-192],[64,-160]],["L",[64,-32]],["Q",[272,-48],[368,-48]],["Q",[384,-48],[400,-32]],["Q",[400,-32],[400,-16]],["L",[400,48]],["Q",[304,16],[224,16]],["L",[192,16]],["Q",[128,16],[80,64]],["Q",[48,112],[48,176]],["L",[48,384]],["Q",[48,448],[80,496]],["Q",[128,544],[208,544]],["L",[576,544]],["L",[576,-32]],["Q",[576,-96],[544,-144]],["Q",[496,-192],[432,-192]]],[["M",[256,160]],["Q",[240,160],[224,176]],["Q",[224,176],[224,192]],["L",[224,368]],["Q",[224,400],[256,400]],["L",[400,400]],["L",[400,176]],["Q",[352,160],[288,160]]]]},"path":"M432 -192Q272 -192 64 -160L64 -32Q272 -48 368 -48Q384 -48 400 -32Q400 -32 400 -16L400 48Q304 16 224 16L192 16Q128 16 80 64Q48 112 48 176L48 384Q48 448 80 496Q128 544 208 544L576 544L576 -32Q576 -96 544 -144Q496 -192 432 -192ZM256 160Q240 160 224 176Q224 176 224 192L224 368Q224 400 256 400L400 400L400 176Q352 160 288 160Z"},{"line":"q⡈M⠹⠕L⠹⠡Q⠳⠟⠮⠟L⠬⠟Q⠨⠟⠥⠢Q⠣⠥⠣⠩L⠣⠸Q⠣⠼⠥⠿Q⠨⡂⠭⡂L⡄⡂L⡄⠕ZM⠰⠨Q⠯⠨⠮⠩Q⠮⠩⠮⠪L⠮⠷Q⠮⠹⠰⠹L⠹⠹L⠹⠩Q⠶⠨⠲⠨Z","decoded":{"letter":"q","adv":640,"contours":[[["M",[400,-176]],["L",[400,16]],["Q",[304,-16],[224,-16]],["L",[192,-16]],["Q",[128,-16],[80,32]],["Q",[48,80],[48,144]],["L",[48,384]],["Q",[48,448],[80,496]],["Q",[128,544],[208,544]],["L",[576,544]],["L",[576,-176]]],[["M",[256,128]],["Q",[240,128],[224,144]],["Q",[224,144],[224,160]],["L",[224,368]],["Q",[224,400],[256,400]],["L",[400,400]],["L",[400,144]],["Q",[352,128],[288,128]]]]},"path":"M400 -176L400 16Q304 -16 224 -16L192 -16Q128 -16 80 32Q48 80 48 144L48 384Q48 448 80 496Q128 544 208 544L576 544L576 -176ZM256 128Q240 128 224 144Q224 144 224 160L224 368Q224 400 256 400L400 400L400 144Q352 128 288 128Z"},{"line":"a⠀M⠀⠀L⠁⠁Z","decoded":{"letter":"a","adv":-512,"contours":[[["M",[-512,-512]],["L",[-496,-496]]]]},"path":"M-512 -512L-496 -496Z"}],"errors":[{"line":"","error":"bad header (letter + advance expected)"},{"line":"a","error":"bad header (letter + advance expected)"},{"line":"1⠀","error":"bad header (letter + advance expected)"},{"line":"a⠀","error":"no contours"},{"line":"a⠀M⠀","error":"coordinate pair expected at 3"},{"line":"a⠀M⠀⠀Z","error":"Z on an empty contour"},{"line":"a⠀L⠀⠀Z","error":"L outside a contour"},{"line":"a⠀M⠀⠀L⠁⠁","error":"unclosed contour at end of line"},{"line":"a⠀M⠀⠀M⠁⠁Z","error":"M inside an open contour"},{"line":"a⠀M⠀⠀L⠁⠁x","error":"unexpected char 'x' at 8"},{"line":"a⠀M⠀⠀Q⠁⠁L","error":"coordinate pair expected at 8"},{"line":"a⠀Q⠀⠀⠁⠁Z","error":"Q outside a contour"},{"line":"a⠀M⠀⠀L⠁⠁ZZ","error":"Z on an empty contour"},{"line":"a⡠M⠀⠀L⠁⠁Z","error":"bad header (letter + advance expected)"},{"line":"a⠀M⠀⠀L⠁⠁Z\n","error":"unexpected char '\\n' at 9"},{"line":"a⠀M⠀⠀L⠁⠁'","error":"unexpected char \"'\" at 8"},{"line":"a⠀M⠀⠀L⠁⠁\\","error":"unexpected char '\\\\' at 8"},{"line":"a⠀M⠀⠀L⠁⠁\t","error":"unexpected char '\\t' at 8"},{"line":"A⠀M⠀⠀L⠁⠁Z","error":"bad header (letter + advance expected)"},{"line":"a⠀M⠀⠀Q⠁⠁⠂⠂ZM⠀⠀L⠁⠁Z","error":null,"decoded":{"letter":"a","adv":-512,"contours":[[["M",[-512,-512]],["Q",[-496,-496],[-480,-480]]],[["M",[-512,-512]],["L",[-496,-496]]]]},"path":"M-512 -512Q-496 -496 -480 -480ZM-512 -512L-496 -496Z"},{"line":"a⠀M⠀⠀Q⠁⠁⠂⠂ZM⠀⠀L⠁","error":"coordinate pair expected at 15"},{"line":"a⡟M⡟⡟L⠀⡟Q⠀⠀⡟⠀Z","error":null,"decoded":{"letter":"a","adv":1008,"contours":[[["M",[1008,1008]],["L",[-512,1008]],["Q",[-512,-512],[1008,-512]]]]},"path":"M1008 1008L-512 1008Q-512 -512 1008 -512Z"}]};

const short = (line) => JSON.stringify(Array.from(line).slice(0, 14).join("")) + (line.length > 14 ? "…" : "");

test("the alphabet is codec.ALPHABET: 127 chars, newline last, coords contiguous", () => {
  assert.equal(ALPHABET, PY.alphabet);
  assert.equal(ALPHABET.length, 127);
  assert.equal(COORDS, PY.coords);
  assert.equal(BOUNDARY_ID, 126);
  assert.equal(new Set(ALPHABET).size, 127);
});

test("unbucket matches codec.unbucket over all 96 buckets", () => {
  const got = Array.from(COORDS, unbucket);
  assert.deepEqual(got, PY.unbucket);
  assert.equal(got[0], -512);
  assert.equal(got[N_BUCKETS - 1], 1008);
  assert.equal(isCoord(String.fromCharCode(0x2800 + 96)), false);
  assert.equal(isCoord("⠀"), true);
});

for (const f of PY.fixtures) {
  test(`decodeGlyph + glyphToSvgPath match Python on ${short(f.line)}`, () => {
    const g = decodeGlyph(f.line);
    assert.deepEqual(g, f.decoded);
    assert.equal(glyphToSvgPath(g), f.path);
  });
}

for (const e of PY.errors) {
  if (e.error === null) {
    test(`grammar accepts ${short(e.line)}`, () => {
      const g = decodeGlyph(e.line);
      assert.deepEqual(g, e.decoded);
      assert.equal(glyphToSvgPath(g), e.path);
    });
  } else {
    test(`grammar rejects ${short(e.line)} — ${e.error}`, () => {
      assert.throws(
        () => decodeGlyph(e.line),
        (err) => err instanceof GlyphSyntaxError && err.message === e.error,
      );
    });
  }
}

test("decodeGlyphPartial never throws on a prefix and agrees with decodeGlyph on the whole line", () => {
  for (const f of PY.fixtures) {
    const chars = Array.from(f.line);
    for (let n = 0; n <= chars.length; n++) {
      const p = decodeGlyphPartial(chars.slice(0, n).join(""));
      assert.ok(Array.isArray(p.contours));
      // whatever it closed so far is a prefix of the finished glyph
      assert.deepEqual(p.contours, f.decoded.contours.slice(0, p.contours.length));
    }
    const whole = decodeGlyphPartial(f.line);
    assert.equal(whole.letter, f.decoded.letter);
    assert.equal(whole.adv, f.decoded.adv);
    assert.deepEqual(whole.contours, f.decoded.contours);
    assert.equal(whole.open, null);
  }
  // a line cut inside a contour: the closed ones are kept, the open one exposed
  const cut = "a⠀M⠀⠀L⠁⠁Q⠂⠂⠃⠃ZM⠄⠄L⠅";
  const p = decodeGlyphPartial(cut);
  assert.equal(p.contours.length, 1);
  assert.deepEqual(p.open, [["M", [-448, -448]]]);
  assert.equal(contourToSvgPath(p.open), "M-448 -448");
  assert.deepEqual(decodeGlyphPartial("").contours, []);
  assert.equal(decodeGlyphPartial("1").letter, null);
  assert.equal(decodeGlyphPartial("x").letter, "x");
  assert.equal(decodeGlyphPartial("x").adv, null);
});

test("glyphToPathCommands / drawGlyphOn reproduce the svg path through the canvas verbs", () => {
  for (const f of PY.fixtures) {
    const g = decodeGlyph(f.line);
    const cmds = glyphToPathCommands(g);
    assert.equal(cmds.filter((c) => c.type === "Z").length, g.contours.length);
    assert.equal(cmds.filter((c) => c.type === "M").length, g.contours.length);
    let d = "";
    const sink = {
      moveTo: (x, y) => (d += `M${x} ${y}`),
      lineTo: (x, y) => (d += `L${x} ${y}`),
      quadraticCurveTo: (x1, y1, x, y) => (d += `Q${x1} ${y1} ${x} ${y}`),
      close: () => (d += "Z"),
    };
    assert.equal(drawGlyphOn(sink, g), sink);
    assert.equal(d, f.path);
  }
});

test("glyphBounds covers every named point", () => {
  const g = decodeGlyph("a⡟M⡟⡟L⠀⡟Q⠀⠀⡟⠀Z");
  assert.deepEqual(glyphBounds(g), { xMin: -512, yMin: -512, xMax: 1008, yMax: 1008 });
  assert.equal(glyphBounds({ contours: [] }), null);
});

test("layoutWord places letters by advance, spaces by a fixed gap, missing letters by a slot", () => {
  const s = decodeGlyph(PY.fixtures[0].line); // an s
  const table = { s, u: null };
  const { items, width, bounds } = layoutWord("su s", (ch) => table[ch] ?? null);
  assert.deepEqual(
    items.map((i) => [i.ch, i.x, i.width, Boolean(i.glyph)]),
    [
      ["s", 0, s.adv, true],
      ["u", s.adv, MISSING_ADVANCE, false],
      [" ", s.adv + MISSING_ADVANCE, SPACE_ADVANCE, false],
      ["s", s.adv + MISSING_ADVANCE + SPACE_ADVANCE, s.adv, true],
    ],
  );
  assert.equal(width, 2 * s.adv + MISSING_ADVANCE + SPACE_ADVANCE);
  const b = glyphBounds(s);
  assert.deepEqual(bounds, {
    xMin: b.xMin,
    yMin: b.yMin,
    xMax: s.adv + MISSING_ADVANCE + SPACE_ADVANCE + b.xMax,
    yMax: b.yMax,
  });
  assert.equal(layoutWord("", () => null).width, 0);
  assert.equal(layoutWord("", () => null).bounds, null);
  // a negative advance never walks the cursor backwards
  const neg = decodeGlyph("a⠀M⠀⠀L⠁⠁Z");
  assert.equal(neg.adv, -512);
  assert.equal(layoutWord("aa", () => neg).items[1].x, 0);
});

test("fontMetrics defaults to 800/-250 and widens to cover overshoot", () => {
  assert.deepEqual(fontMetrics([]), { ascender: 800, descender: -250 });
  const tall = decodeGlyph("a⡟M⡟⡟L⠀⡟Q⠀⠀⡟⠀Z");
  assert.deepEqual(fontMetrics([tall]), { ascender: 1008, descender: -512 });
  const s = decodeGlyph(PY.fixtures[0].line);
  assert.deepEqual(fontMetrics([s]), { ascender: 800, descender: -250 });
});

test("windForNonzero: a counter inside a bowl is wound against it; reversal is exact", () => {
  // outer square (clockwise in y-up), inner square (also clockwise, as the codec writes every contour)
  const outer = [["M", [-512, -512]], ["L", [-512, -256]], ["L", [-256, -256]], ["L", [-256, -512]]];
  const inner = [["M", [-448, -448]], ["L", [-448, -320]], ["Q", [-384, -320], [-320, -320]], ["L", [-320, -448]]];
  const w = windForNonzero({ letter: "o", adv: 300, contours: [outer, inner] });
  assert.deepEqual(w.contours[0], outer); // depth 0: stays clockwise
  assert.deepEqual(w.contours[1], reverseContour(inner)); // depth 1: reversed
  assert.deepEqual(w.contours[1], [
    ["M", [-320, -448]],
    ["L", [-320, -320]],
    ["Q", [-384, -320], [-448, -320]],
    ["L", [-448, -448]],
  ]);
  assert.deepEqual(reverseContour(reverseContour(inner)), inner);
  // a counter-clockwise outer is flipped to clockwise
  const ccw = [["M", [0, 0]], ["L", [256, 0]], ["L", [256, 256]], ["L", [0, 256]]];
  assert.deepEqual(windForNonzero({ contours: [ccw] }).contours[0], reverseContour(ccw));
  // every corpus fixture survives the pass with its contour and segment counts intact
  for (const f of PY.fixtures) {
    const d = decodeGlyph(f.line);
    const ww = windForNonzero(d);
    assert.equal(ww.contours.length, d.contours.length);
    for (let i = 0; i < d.contours.length; i++) assert.equal(ww.contours[i].length, d.contours[i].length);
  }
});
