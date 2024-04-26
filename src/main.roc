app "roc-packages"
    packages {
        cli: "https://github.com/roc-lang/basic-cli/releases/download/0.9.0/oKWkaruh2zXxin_xfsYsCJobH1tO8_JvNkFzDwwzNUQ.tar.br",
        html: "https://github.com/Hasnep/roc-html/releases/download/v0.4.0/sS6DMu08ogvM7j5S4E-A6VwdwQiVPlh6DbrTHbBAhZw.tar.br",
        svg: "https://github.com/Hasnep/roc-svg/releases/download/v0.0.7/vVYSN9mO3igMwoYeu9RtQAnfVFk0Ur2DGWkX9gwHzIE.tar.br",
    }
    imports [
        cli.File,
        cli.Path,
        cli.Stdout,
        cli.Task,
        html.Html,
        html.Attribute,
        Data.{ data, Repo, Release },
        Icon,
    ]
    provides [main] to cli

copyButtonComponent = \textToCopy ->
    js = Str.joinWith ["try {navigator.clipboard.writeText(`", textToCopy, "`);} catch (e) {};"] ""
    attributeOnClick = Attribute.attribute "onClick"
    Html.button [attributeOnClick js] [Html.text "Copy"]

releaseComponent : Release -> Html.Node
releaseComponent =
    \release ->
        version = Str.concat "v" release.version
        releaseLinkElement =
            when release.url is
                Url releaseUrl -> Html.a [Attribute.href releaseUrl] [Html.text version]
        assetElements =
            when release.asset is
                Url assetUrl -> [copyButtonComponent assetUrl, Html.text " ", Html.code [] [Html.text assetUrl]]
                NoAssetUrl -> []
        Html.li [] [releaseLinkElement, Html.p [] assetElements]

repoComponent : Repo -> Html.Node
repoComponent = \repo ->
    fullName = ([repo.owner, repo.name] |> Str.joinWith "/")
    docsElement =
        when repo.homepage is
            Url url -> Html.a [Attribute.href url] [Icon.book]
            NoHomepage -> Html.text ""
    repoElement =
        (Url githubUrl) = repo.github
        Html.a [Attribute.href githubUrl] [Icon.github]
    Html.li [] [
        Html.h2 [Attribute.id fullName] [Html.text fullName, Html.text " ", docsElement, Html.text " ", repoElement],
        Html.p [] [Html.text repo.description],
        Html.ul [] (List.map repo.releases releaseComponent),
    ]

main =
    repos =
        data.repos
        |> List.keepIf (\repo -> List.len repo.releases > 0)
        |> List.sortWith (\a, b -> Num.compare a.updatedAt b.updatedAt)
        |> List.reverse
    tableOfContentsElement = Html.ul
        []
        (
            List.map
                repos
                (\repo ->
                    fullName = ([repo.owner, repo.name] |> Str.joinWith "/")
                    Html.li [] [Html.a [Attribute.href (Str.concat "#" fullName)] [Html.text fullName]])
        )
    headElement = Html.head [] [
        Html.meta [Attribute.charset "utf-8"],
        Html.title [] [Html.text "Roc Packages"],
        Html.link [
            Attribute.rel "stylesheet",
            Attribute.href "https://cdn.jsdelivr.net/npm/purecss@3.0.0/build/base-min.css",
        ],
        Html.style [] [Html.text "main {max-width: 800px; margin: auto;} ul.packages {list-style-type: none;}"],
    ]
    bodyElement = Html.body [] [
        Html.main [] [
            Html.h1 [] [Html.text "Roc Packages"],
            Html.p [] [Html.text "An unofficial package website for Roc, including libraries and platforms."],
            Html.p [] [
                Html.text "This website was automatically generated on ",
                Html.text data.updatedAt,
                Html.text ". ",
                Html.text "Source code for this website can be found on ",
                Html.a [Attribute.href "https://github.com/Hasnep/roc-packages"] [Html.text "GitHub"],
                Html.text ". ",
                Html.text "The data for this website are also available as JSON at ",
                Html.a [Attribute.href "/data.json"] [Html.text "/data.json"],
                Html.text ".",
            ],
            Html.p
                []
                [
                    Html.text "Made by ",
                    Html.a [Attribute.href "https://ha.nnes.dev"] [Html.text "Hannes"],
                    Html.text ".",
                ],
            Html.h2
                []
                [Html.text "Index"],
            tableOfContentsElement,
            Html.ul [Attribute.class "packages"] (List.map repos repoComponent),

        ],
    ]
    indexPage = Html.html [Attribute.lang "en"] [headElement, bodyElement] |> Html.render
    result <- File.writeUtf8 (Path.fromStr "dist/index.html") indexPage |> Task.attempt
    when result is
        Ok _ -> Stdout.line "Done!"
        Err _ -> crash "oh no"
