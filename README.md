# tramuel.com

Notes From Here, built with [Hugo](https://gohugo.io) and the
[Noesis](https://github.com/josephhutch/noesis) theme by Joe Hutchinson (MIT license).
The theme is untouched in `themes/noesis`. Every change for this site lives in
`layouts/` and `assets/css/override.css`.

## Where things are

- `content/iam/`: blog posts, one folder per post (`index.md` plus its images). The folder path is the URL.
- `content/eye-tramuel/`, `content/recipes/`, `content/bibliophile/`: the other Squarespace blogs. They share the one feed.
- `content/about/`, `content/eyetramuel/`: pages in the menu.
- `content/_index.md`: home page text. The cover art goes at `content/cover.jpg`.
- `hugo.toml`: site settings and the menu (Blog, About, Eyetramuel).
- `tools/`: the converter used on the Squarespace export, and `image-manifest.json`, the list of images still hosted on Squarespace.

## Seeing it on your Mac

Double-click `preview.command`. The first time, it downloads Hugo into
`tools/bin` (about a minute). Then the site opens at http://localhost:1313 and
updates whenever a file changes. Close the Terminal window to stop it.

## Writing a post

Make a folder in `content/iam/` named for the URL you want, for example
`content/iam/fifty-times/`. Put the post in `index.md` with this at the top:

```
---
title: Fifty Times
date: 2026-11-22T08:00:00-05:00
categories: [Essay]
---
```

Then the text in Markdown, which is what Bear exports. Images go in the same
folder and the first one becomes the thumbnail. To use a different thumbnail,
add `thumbnail: that-photo.jpg` to the top section. For audio, put the file in
the folder and write `{{< audio src="memo.m4a" >}}` where it should play.

## Before canceling Squarespace

Old posts still load their images from Squarespace's servers. All 2,076 are
listed in `tools/image-manifest.json` and need to be copied into the post
folders before the Squarespace plan ends.
