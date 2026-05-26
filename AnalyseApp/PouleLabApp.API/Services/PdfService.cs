using Microsoft.EntityFrameworkCore;
using PouleLabApp.API.Data;
using PouleLabApp.API.Models;
using PouleLabApp.API.Services.Interfaces;
using QuestPDF.Fluent;
using QuestPDF.Helpers;
using QuestPDF.Infrastructure;

namespace PouleLabApp.API.Services
{
    public class PdfService : IPdfService
    {
        private readonly ApplicationDbContext _context;

        public PdfService(ApplicationDbContext context)
        {
            QuestPDF.Settings.License = LicenseType.Community;
            _context = context;
        }

        public byte[] GenerateRequestFormPdf(int requestId)
        {
            var request = _context.AnalysisRequests
                .Include(r => r.Client)
                .Include(r => r.Laboratory)
                .Include(r => r.Samples)
                    .ThenInclude(s => s.Results)
                .FirstOrDefault(r => r.Id == requestId)
                ?? throw new KeyNotFoundException("Demande introuvable.");

            return request.Laboratory?.TemplateType switch
            {
                FormTemplateType.DICK   => GenerateDickFormPdf(request),
                FormTemplateType.GIPA   => GenerateIndustrialFormPdf(request, "GIPA",   "#7C3AED", "Huiles & Lubrifiants"),
                FormTemplateType.MEDOIL => GenerateIndustrialFormPdf(request, "MEDOIL", "#B45309", "Corps Gras & Huiles Alimentaires"),
                _                      => GenerateIndustrialFormPdf(request, "SNA",    "#1E3A8A", "Analyses Industrielles"),
            };
        }

        public byte[] GenerateBulletinPdf(int requestId)
        {
            var request = _context.AnalysisRequests
                .Include(r => r.Client)
                .Include(r => r.Laboratory)
                .Include(r => r.Samples)
                    .ThenInclude(s => s.Results)
                .FirstOrDefault(r => r.Id == requestId)
                ?? throw new KeyNotFoundException("Demande introuvable.");

            if (request.Status != RequestStatus.Validated)
                throw new ArgumentException(
                    "Le bulletin n'est disponible que pour les demandes validées.");

            return GenerateBulletinDocument(request);
        }

        // -------------------------------------------------------
        // TEMPLATE DICK
        // -------------------------------------------------------
        private static byte[] GenerateDickFormPdf(AnalysisRequest request)
        {
            return Document.Create(container =>
            {
                container.Page(page =>
                {
                    page.Size(PageSizes.A4);
                    page.Margin(1.5f, Unit.Centimetre);
                    page.DefaultTextStyle(x => x.FontSize(9).FontFamily("Arial"));

                    page.Header().Column(col =>
                    {
                        col.Item().Border(1.5f).BorderColor("#991B1B").Row(row =>
                        {
                            row.ConstantItem(170).Background("#991B1B").Padding(10).Column(c =>
                            {
                                c.Item().Text("SOCIÉTÉ DICK")
                                    .Bold().FontSize(12).FontColor("#FFFFFF");
                                c.Item().Text("LABORATOIRE VÉTÉRINAIRE")
                                    .FontSize(8).FontColor("#FCA5A5");
                                c.Item().PaddingTop(4).Text("FICHE DE RENSEIGNEMENTS")
                                    .Bold().FontSize(9).FontColor("#FCD34D");
                            });

                            row.RelativeItem().Padding(10).Column(c =>
                            {
                                c.Item().AlignCenter()
                                    .Text("FICHE DE DEMANDE D'ANALYSE")
                                    .Bold().FontSize(13).FontColor("#991B1B");
                                c.Item().PaddingTop(2).AlignCenter()
                                    .Text($"N° {request.Id:D6}")
                                    .Bold().FontSize(12).FontColor("#374151");
                                c.Item().PaddingTop(2).AlignCenter()
                                    .Text($"Date : {request.SubmittedAt:dd/MM/yyyy}")
                                    .FontSize(9).FontColor("#6B7280");
                            });

                            row.ConstantItem(130).Padding(8).Column(c =>
                            {
                                c.Item().Text("N° DE RÉCEPTION")
                                    .Bold().FontSize(7).FontColor("#6B7280");
                                c.Item().PaddingTop(2).Border(1)
                                    .BorderColor("#991B1B").Background("#FFF5F5")
                                    .Padding(5).Text($"{request.Id:D6}")
                                    .Bold().FontSize(13).FontColor("#991B1B");
                                c.Item().PaddingTop(4).Text("STATUT")
                                    .Bold().FontSize(7).FontColor("#6B7280");
                                c.Item().PaddingTop(2)
                                    .Text(request.Status.ToString().ToUpper())
                                    .Bold().FontSize(8).FontColor("#F59E0B");
                            });
                        });
                        col.Item().PaddingTop(4);
                    });

                    page.Content().Column(col =>
                    {
                        // SECTION I — RENSEIGNEMENTS DEMANDEUR
                        col.Item().Border(1).BorderColor("#D1D5DB").Column(section =>
                        {
                            section.Item().Background("#991B1B").Padding(4)
                                .Text("I. RENSEIGNEMENTS SUR LE DEMANDEUR")
                                .Bold().FontSize(9).FontColor("#FFFFFF");

                            section.Item().Padding(8).Element(container =>
                                RenderInfoTable(container, new List<(string, string)>
                                {
                                    ("NOM ET PRÉNOM :", $"{request.Client?.FirstName} {request.Client?.LastName}"),
                                    ("N° DEMANDE :", $"{request.Id:D6}"),
                                    ("EMAIL :", request.Client?.Email ?? ""),
                                    ("DATE :", request.CreatedAt.ToString("dd/MM/yyyy HH:mm")),
                                    ("FILIALE / SOCIÉTÉ :", request.Client?.FilialeName ?? ""),
                                    ("LABORATOIRE :", "DICK")
                                }));
                        });

                        col.Item().PaddingTop(5);

                        // SECTION II — IDENTIFICATION DU CENTRE
                        col.Item().Border(1).BorderColor("#D1D5DB").Column(section =>
                        {
                            section.Item().Background("#7F1D1D").Padding(4)
                                .Text("II. IDENTIFICATION DU CENTRE")
                                .Bold().FontSize(9).FontColor("#FFFFFF");

                            section.Item().Padding(8).Element(container =>
                                RenderInfoTable(container, new List<(string, string)>
                                {
                                    ("CENTRE N° :", "..............................."),
                                    ("N° ROTATION :", "..............................."),
                                    ("SPÉCULATION :", "..............................."),
                                    ("ORIGINE REPRO :", "..............................."),
                                    ("ORIGINE COUVOIR :", "..............................."),
                                    ("SOUCHE :", "..............................."),
                                    ("ÂGE :", "..............................."),
                                    ("EFFECTIF DÉPART :", "..............................."),
                                    ("EFFECTIF RESTANT :", "...............................")
                                }));
                        });

                        col.Item().PaddingTop(5);

                        // SECTION III — ÉCHANTILLONS ENVOYÉS
                        col.Item().Border(1).BorderColor("#D1D5DB").Column(section =>
                        {
                            section.Item().Background("#7F1D1D").Padding(4)
                                .Text("III. ÉCHANTILLONS ENVOYÉS")
                                .Bold().FontSize(9).FontColor("#FFFFFF");

                            section.Item().Padding(8).Column(sCol =>
                            {
                                sCol.Item().Row(row =>
                                {
                                    foreach (var sample in request.Samples)
                                    {
                                        row.AutoItem().Padding(3).Row(r =>
                                        {
                                            r.ConstantItem(12).Height(12)
                                                .Border(1).BorderColor("#991B1B")
                                                .Background("#FFF5F5").AlignCenter()
                                                .AlignMiddle().Text("✓")
                                                .FontSize(8).FontColor("#991B1B");
                                            r.AutoItem().PaddingLeft(4)
                                                .Text($"{sample.Type} ({sample.Quantity} {sample.Unit})")
                                                .FontSize(8);
                                        });
                                    }
                                });

                                sCol.Item().PaddingTop(6).Table(table =>
                                {
                                    table.ColumnsDefinition(c =>
                                    {
                                        c.ConstantColumn(25);
                                        c.RelativeColumn(2);
                                        c.RelativeColumn(3);
                                        c.RelativeColumn(1);
                                        c.RelativeColumn(1);
                                    });

                                    table.Header(h =>
                                    {
                                        foreach (var t in new[] {
                                            "N°", "TYPE", "CARACTÉRISTIQUES",
                                            "QUANTITÉ", "UNITÉ" })
                                        {
                                            h.Cell().Background("#FECACA")
                                                .BorderBottom(1).BorderColor("#FCA5A5")
                                                .Padding(4).Text(t).Bold()
                                                .FontSize(8).FontColor("#7F1D1D");
                                        }
                                    });

                                    var idx = 1;
                                    foreach (var sample in request.Samples)
                                    {
                                        var bg = idx % 2 == 0 ? "#FFF5F5" : "#FFFFFF";
                                        table.Cell().Background(bg).BorderBottom(1)
                                            .BorderColor("#FEE2E2").Padding(4)
                                            .AlignCenter().Text(idx.ToString())
                                            .Bold().FontSize(8);
                                        table.Cell().Background(bg).BorderBottom(1)
                                            .BorderColor("#FEE2E2").Padding(4)
                                            .Text(sample.Type).Bold().FontSize(8);
                                        table.Cell().Background(bg).BorderBottom(1)
                                            .BorderColor("#FEE2E2").Padding(4)
                                            .Text(sample.Characteristics).FontSize(8);
                                        table.Cell().Background(bg).BorderBottom(1)
                                            .BorderColor("#FEE2E2").Padding(4)
                                            .AlignCenter()
                                            .Text(sample.Quantity.ToString("F1"))
                                            .FontSize(8);
                                        table.Cell().Background(bg).BorderBottom(1)
                                            .BorderColor("#FEE2E2").Padding(4)
                                            .AlignCenter().Text(sample.Unit).FontSize(8);
                                        idx++;
                                    }
                                });
                            });
                        });

                        col.Item().PaddingTop(5);

                        // SECTION IV — SYMPTÔMES OBSERVÉS
                        col.Item().Border(1).BorderColor("#D1D5DB").Column(section =>
                        {
                            section.Item().Background("#7F1D1D").Padding(4)
                                .Text("IV. SYMPTÔMES OBSERVÉS")
                                .Bold().FontSize(9).FontColor("#FFFFFF");

                            section.Item().Padding(8).Column(sCol =>
                            {
                                var symptoms = new[] {
                                    "Nonchalance", "Éternuement", "Torticolis",
                                    "Tremblement", "Boiterie", "Écoulement nasal",
                                    "Diarrhée", "Paralysie", "Œufs déformés",
                                    "Coquilles fragiles", "Œufs sans coquille", "Autres"
                                };

                                sCol.Item().Row(row =>
                                {
                                    row.RelativeItem().Column(c =>
                                    {
                                        foreach (var s in symptoms.Take(4))
                                            AddCheckbox(c, s);
                                    });
                                    row.RelativeItem().Column(c =>
                                    {
                                        foreach (var s in symptoms.Skip(4).Take(4))
                                            AddCheckbox(c, s);
                                    });
                                    row.RelativeItem().Column(c =>
                                    {
                                        foreach (var s in symptoms.Skip(8))
                                            AddCheckbox(c, s);
                                    });
                                });

                                sCol.Item().PaddingTop(6).Row(r =>
                                {
                                    r.AutoItem()
                                        .Text("DATE D'APPARITION DE L'ANOMALIE : ")
                                        .Bold().FontSize(8);
                                    r.RelativeItem().BorderBottom(1)
                                        .BorderColor("#D1D5DB").Text("").FontSize(8);
                                });
                            });
                        });

                        col.Item().PaddingTop(5);

                        // SECTION V — ANALYSES DEMANDÉES
                        col.Item().Border(1).BorderColor("#D1D5DB").Column(section =>
                        {
                            section.Item().Background("#7F1D1D").Padding(4)
                                .Text("V. ANALYSES DEMANDÉES")
                                .Bold().FontSize(9).FontColor("#FFFFFF");

                            section.Item().Padding(8).Column(sCol =>
                            {
                                var idx = 1;
                                foreach (var sample in request.Samples)
                                {
                                    sCol.Item().PaddingBottom(4).Column(sc =>
                                    {
                                        sc.Item().Background("#FEF2F2").Padding(4)
                                            .Text($"Échantillon {idx} : {sample.Type}")
                                            .Bold().FontSize(9).FontColor("#991B1B");

                                        sc.Item().PaddingTop(4).Row(row =>
                                        {
                                            foreach (var result in sample.Results)
                                            {
                                                row.AutoItem().Padding(3).Row(r =>
                                                {
                                                    r.ConstantItem(12).Height(12)
                                                        .Border(1).BorderColor("#991B1B")
                                                        .Background("#FEE2E2")
                                                        .AlignCenter().AlignMiddle()
                                                        .Text("✓").FontSize(8)
                                                        .FontColor("#991B1B");
                                                    r.AutoItem().PaddingLeft(4)
                                                        .Text(result.AnalysisName ?? "")
                                                        .FontSize(8);
                                                });
                                            }
                                        });
                                    });
                                    idx++;
                                }
                            });
                        });

                        col.Item().PaddingTop(5);

                        // SECTION VI — OBSERVATIONS + SIGNATURES
                        col.Item().Border(1).BorderColor("#D1D5DB").Column(section =>
                        {
                            section.Item().Background("#7F1D1D").Padding(4)
                                .Text("VI. OBSERVATIONS ET SIGNATURE")
                                .Bold().FontSize(9).FontColor("#FFFFFF");

                            section.Item().Row(row =>
                            {
                                row.RelativeItem().BorderRight(1)
                                    .BorderColor("#D1D5DB").Padding(8).Column(c =>
                                {
                                    c.Item().Text("OBSERVATIONS / SUSPICION :")
                                        .Bold().FontSize(8);
                                    c.Item().PaddingTop(4).MinHeight(50)
                                        .Border(1).BorderColor("#E5E7EB")
                                        .Background("#FFFBEB").Padding(4)
                                        .Text(string.IsNullOrEmpty(request.Notes)
                                            ? "" : request.Notes)
                                        .FontSize(8);
                                });

                                row.RelativeItem().Padding(8).Column(c =>
                                {
                                    c.Item().Text(
                                        $"NOM : {request.Client?.FirstName} {request.Client?.LastName}")
                                        .FontSize(8);
                                    c.Item().PaddingTop(4)
                                        .Text($"DATE : {request.SubmittedAt:dd/MM/yyyy}")
                                        .FontSize(8);
                                    c.Item().PaddingTop(4)
                                        .Text("SIGNATURE : _______________________")
                                        .FontSize(8).FontColor("#9CA3AF");
                                    c.Item().PaddingTop(8)
                                        .Text("RÉSERVÉ AU LABORATOIRE :")
                                        .Bold().FontSize(8);
                                    c.Item().PaddingTop(2)
                                        .Text("Date réception : ___/___/______")
                                        .FontSize(8).FontColor("#9CA3AF");
                                    c.Item().PaddingTop(2)
                                        .Text("Cachet : ").FontSize(8).FontColor("#9CA3AF");
                                    c.Item().PaddingTop(2).MinHeight(20)
                                        .Border(1).BorderColor("#E5E7EB")
                                        .Background("#F9FAFB");
                                });
                            });
                        });
                    });

                    page.Footer().PaddingTop(4).BorderTop(1)
                        .BorderColor("#FCA5A5").Row(row =>
                    {
                        row.RelativeItem()
                            .Text("DICK — Poulina Group Holding | Laboratoire Vétérinaire")
                            .FontSize(7).FontColor("#9CA3AF");
                        row.AutoItem().Text(text =>
                        {
                            text.Span("Page ").FontSize(7).FontColor("#9CA3AF");
                            text.CurrentPageNumber().FontSize(7).FontColor("#9CA3AF");
                            text.Span(" / ").FontSize(7).FontColor("#9CA3AF");
                            text.TotalPages().FontSize(7).FontColor("#9CA3AF");
                        });
                        row.RelativeItem().AlignRight()
                            .Text($"Réf : DICK-{request.Id:D6}-{DateTime.UtcNow:yyyyMMdd}")
                            .FontSize(7).FontColor("#9CA3AF");
                    });
                });
            }).GeneratePdf();
        }

        // -------------------------------------------------------
        // TEMPLATE INDUSTRIEL — SNA / GIPA / MEDOIL
        // -------------------------------------------------------
        private static byte[] GenerateIndustrialFormPdf(
            AnalysisRequest request,
            string labName,
            string accentColor,
            string labSpecialty)
        {
            return Document.Create(container =>
            {
                container.Page(page =>
                {
                    page.Size(PageSizes.A4);
                    page.Margin(1.5f, Unit.Centimetre);
                    page.DefaultTextStyle(x => x.FontSize(9).FontFamily("Arial"));

                    page.Header().Column(col =>
                    {
                        col.Item().Border(1.5f).BorderColor(accentColor).Row(row =>
                        {
                            row.ConstantItem(170).Background(accentColor)
                                .Padding(10).Column(c =>
                            {
                                c.Item().Text("POULINA GROUP HOLDING")
                                    .Bold().FontSize(10).FontColor("#FFFFFF");
                                c.Item().Text(labSpecialty)
                                    .FontSize(8).FontColor("#E5E7EB");
                                c.Item().PaddingTop(4).Text(labName)
                                    .Bold().FontSize(13).FontColor("#FCD34D");
                            });

                            row.RelativeItem().Padding(10).Column(c =>
                            {
                                c.Item().AlignCenter()
                                    .Text("FICHE DE DEMANDE D'ANALYSE")
                                    .Bold().FontSize(13).FontColor(accentColor);
                                c.Item().PaddingTop(2).AlignCenter()
                                    .Text($"N° {request.Id:D6}")
                                    .Bold().FontSize(12).FontColor("#374151");
                                c.Item().PaddingTop(2).AlignCenter()
                                    .Text($"Date : {request.SubmittedAt:dd/MM/yyyy}")
                                    .FontSize(9).FontColor("#6B7280");
                            });

                            row.ConstantItem(130).Padding(8).Column(c =>
                            {
                                c.Item().Border(1).BorderColor(accentColor)
                                    .Padding(5).Column(inner =>
                                {
                                    inner.Item().Text("N° DE RÉCEPTION")
                                        .Bold().FontSize(7).FontColor("#6B7280");
                                    inner.Item().PaddingTop(2)
                                        .Text($"{request.Id:D6}")
                                        .Bold().FontSize(13).FontColor(accentColor);
                                    inner.Item().PaddingTop(4).Text("STATUT")
                                        .Bold().FontSize(7).FontColor("#6B7280");
                                    inner.Item().PaddingTop(2)
                                        .Text(request.Status.ToString().ToUpper())
                                        .Bold().FontSize(8).FontColor("#F59E0B");
                                });
                            });
                        });
                        col.Item().PaddingTop(4);
                    });

                    page.Content().Column(col =>
                    {
                        // SECTION I — RENSEIGNEMENTS DEMANDEUR
                        col.Item().Border(1).BorderColor("#D1D5DB").Column(section =>
                        {
                            section.Item().Background(accentColor).Padding(4)
                                .Text("I. RENSEIGNEMENTS SUR LE DEMANDEUR")
                                .Bold().FontSize(9).FontColor("#FFFFFF");

                            section.Item().Padding(8).Element(container =>
                                RenderInfoTable(container, new List<(string, string)>
                                {
                                    ("NOM ET PRÉNOM :", $"{request.Client?.FirstName} {request.Client?.LastName}"),
                                    ("N° DEMANDE :", $"{request.Id:D6}"),
                                    ("EMAIL :", request.Client?.Email ?? ""),
                                    ("DATE :", request.CreatedAt.ToString("dd/MM/yyyy HH:mm")),
                                    ("FILIALE / SOCIÉTÉ :", request.Client?.FilialeName ?? ""),
                                    ("LABORATOIRE :", labName)
                                }));
                        });

                        col.Item().PaddingTop(5);

                        // SECTION II — PROVENANCE DES ÉCHANTILLONS
                        col.Item().Border(1).BorderColor("#D1D5DB").Column(section =>
                        {
                            section.Item().Background(accentColor).Padding(4)
                                .Text("II. PROVENANCE DES ÉCHANTILLONS")
                                .Bold().FontSize(9).FontColor("#FFFFFF");

                            section.Item().Padding(8).Element(container =>
                                RenderInfoTable(container, new List<(string, string)>
                                {
                                    ("SITE DE PRÉLÈVEMENT :", "..............................."),
                                    ("N° LOT / RÉFÉRENCE :", "..............................."),
                                    ("DATE DE PRÉLÈVEMENT :", "..............................."),
                                    ("CONDITIONS DE STOCKAGE :", "...............................")
                                }));
                        });

                        col.Item().PaddingTop(5);

                        // SECTION III — ÉCHANTILLONS
                        col.Item().Border(1).BorderColor("#D1D5DB").Column(section =>
                        {
                            section.Item().Background(accentColor).Padding(4)
                                .Text("III. ÉCHANTILLONS ENVOYÉS")
                                .Bold().FontSize(9).FontColor("#FFFFFF");

                            section.Item().Table(table =>
                            {
                                table.ColumnsDefinition(c =>
                                {
                                    c.ConstantColumn(25);
                                    c.RelativeColumn(2);
                                    c.RelativeColumn(3);
                                    c.RelativeColumn(1);
                                    c.RelativeColumn(1);
                                });

                                table.Header(h =>
                                {
                                    foreach (var t in new[] {
                                        "N°", "TYPE D'ÉCHANTILLON",
                                        "CARACTÉRISTIQUES", "QUANTITÉ", "UNITÉ" })
                                    {
                                        h.Cell().Background("#DBEAFE")
                                            .BorderBottom(1).BorderColor("#93C5FD")
                                            .Padding(4).Text(t).Bold()
                                            .FontSize(8).FontColor(accentColor);
                                    }
                                });

                                var idx = 1;
                                foreach (var sample in request.Samples)
                                {
                                    var bg = idx % 2 == 0 ? "#F8FAFC" : "#FFFFFF";
                                    table.Cell().Background(bg).BorderBottom(1)
                                        .BorderColor("#E5E7EB").Padding(4)
                                        .AlignCenter().Text(idx.ToString())
                                        .Bold().FontSize(8);
                                    table.Cell().Background(bg).BorderBottom(1)
                                        .BorderColor("#E5E7EB").Padding(4)
                                        .Text(sample.Type).Bold().FontSize(8);
                                    table.Cell().Background(bg).BorderBottom(1)
                                        .BorderColor("#E5E7EB").Padding(4)
                                        .Text(sample.Characteristics).FontSize(8);
                                    table.Cell().Background(bg).BorderBottom(1)
                                        .BorderColor("#E5E7EB").Padding(4)
                                        .AlignCenter()
                                        .Text(sample.Quantity.ToString("F1"))
                                        .FontSize(8);
                                    table.Cell().Background(bg).BorderBottom(1)
                                        .BorderColor("#E5E7EB").Padding(4)
                                        .AlignCenter().Text(sample.Unit).FontSize(8);
                                    idx++;
                                }
                            });
                        });

                        col.Item().PaddingTop(5);

                        // SECTION IV — ANALYSES DEMANDÉES
                        col.Item().Border(1).BorderColor("#D1D5DB").Column(section =>
                        {
                            section.Item().Background(accentColor).Padding(4)
                                .Text("IV. ANALYSES DEMANDÉES")
                                .Bold().FontSize(9).FontColor("#FFFFFF");

                            var sampleIndex = 1;
                            foreach (var sample in request.Samples)
                            {
                                section.Item().Padding(6).Column(sCol =>
                                {
                                    sCol.Item().Background("#EFF6FF").Padding(4)
                                        .Text($"Échantillon {sampleIndex} : {sample.Type}")
                                        .Bold().FontSize(9).FontColor(accentColor);

                                    sCol.Item().PaddingTop(4).Row(row =>
                                    {
                                        foreach (var result in sample.Results)
                                        {
                                            row.AutoItem().Padding(3).Row(r =>
                                            {
                                                r.ConstantItem(12).Height(12)
                                                    .Border(1).BorderColor(accentColor)
                                                    .Background("#DBEAFE")
                                                    .AlignCenter().AlignMiddle()
                                                    .Text("✓").FontSize(8)
                                                    .FontColor(accentColor);
                                                r.AutoItem().PaddingLeft(4)
                                                    .Text(result.AnalysisName ?? "")
                                                    .FontSize(8);
                                            });
                                        }
                                    });

                                    sCol.Item().PaddingTop(4).Table(table =>
                                    {
                                        table.ColumnsDefinition(c =>
                                        {
                                            c.RelativeColumn(3);
                                            c.RelativeColumn(1);
                                            c.RelativeColumn(1);
                                            c.RelativeColumn(1);
                                        });

                                        table.Header(h =>
                                        {
                                            foreach (var t in new[] {
                                                "TYPE D'ANALYSE",
                                                "MIN REF", "MAX REF", "UNITÉ" })
                                            {
                                                h.Cell().Background("#F3F4F6")
                                                    .BorderBottom(1).BorderColor("#D1D5DB")
                                                    .Padding(4).Text(t).Bold()
                                                    .FontSize(8).FontColor("#374151");
                                            }
                                        });

                                        foreach (var result in sample.Results)
                                        {
                                            table.Cell().BorderBottom(1)
                                                .BorderColor("#E5E7EB").Padding(4)
                                                .Text(result.AnalysisName ?? "")
                                                .FontSize(8);
                                            table.Cell().BorderBottom(1)
                                                .BorderColor("#E5E7EB").Padding(4)
                                                .AlignCenter()
                                                .Text(result.LowerBound.ToString("F2"))
                                                .FontSize(8);
                                            table.Cell().BorderBottom(1)
                                                .BorderColor("#E5E7EB").Padding(4)
                                                .AlignCenter()
                                                .Text(result.UpperBound.ToString("F2"))
                                                .FontSize(8);
                                            table.Cell().BorderBottom(1)
                                                .BorderColor("#E5E7EB").Padding(4)
                                                .AlignCenter()
                                                .Text(result.Unit ?? "")
                                                .FontSize(8);
                                        }
                                    });
                                });
                                sampleIndex++;
                            }
                        });

                        col.Item().PaddingTop(5);

                        // SECTION V — OBSERVATIONS + SIGNATURES
                        col.Item().Border(1).BorderColor("#D1D5DB").Row(row =>
                        {
                            row.RelativeItem().BorderRight(1)
                                .BorderColor("#D1D5DB").Padding(8).Column(c =>
                            {
                                c.Item().Text("OBSERVATIONS / NOTES :")
                                    .Bold().FontSize(8).FontColor("#374151");
                                c.Item().PaddingTop(4).MinHeight(50)
                                    .Border(1).BorderColor("#E5E7EB")
                                    .Background("#FFFBEB").Padding(4)
                                    .Text(string.IsNullOrEmpty(request.Notes)
                                        ? "" : request.Notes)
                                    .FontSize(8);
                            });

                            row.RelativeItem().Padding(8).Column(c =>
                            {
                                c.Item()
                                    .Text($"NOM : {request.Client?.FirstName} {request.Client?.LastName}")
                                    .FontSize(8);
                                c.Item().PaddingTop(4)
                                    .Text($"DATE : {request.SubmittedAt:dd/MM/yyyy}")
                                    .FontSize(8);
                                c.Item().PaddingTop(8)
                                    .Text("SIGNATURE : _______________________")
                                    .FontSize(8).FontColor("#9CA3AF");
                                c.Item().PaddingTop(8)
                                    .Text("RÉSERVÉ AU LABORATOIRE :")
                                    .Bold().FontSize(8);
                                c.Item().PaddingTop(2)
                                    .Text("Date réception : ___/___/______")
                                    .FontSize(8).FontColor("#9CA3AF");
                                c.Item().PaddingTop(4).MinHeight(25)
                                    .Border(1).BorderColor("#E5E7EB")
                                    .Background("#F9FAFB");
                            });
                        });
                    });

                    page.Footer().PaddingTop(4).BorderTop(1)
                        .BorderColor("#E5E7EB").Row(row =>
                    {
                        row.RelativeItem()
                            .Text($"{labName} — Poulina Group Holding | {labSpecialty}")
                            .FontSize(7).FontColor("#9CA3AF");
                        row.AutoItem().Text(text =>
                        {
                            text.Span("Page ").FontSize(7).FontColor("#9CA3AF");
                            text.CurrentPageNumber().FontSize(7).FontColor("#9CA3AF");
                            text.Span(" / ").FontSize(7).FontColor("#9CA3AF");
                            text.TotalPages().FontSize(7).FontColor("#9CA3AF");
                        });
                        row.RelativeItem().AlignRight()
                            .Text($"Réf : {labName}-{request.Id:D6}-{DateTime.UtcNow:yyyyMMdd}")
                            .FontSize(7).FontColor("#9CA3AF");
                    });
                });
            }).GeneratePdf();
        }

        // -------------------------------------------------------
        // BULLETIN DE RÉSULTATS
        // -------------------------------------------------------
        private static byte[] GenerateBulletinDocument(AnalysisRequest request)
        {
            var accentColor = request.Laboratory?.TemplateType switch
            {
                FormTemplateType.DICK   => "#991B1B",
                FormTemplateType.GIPA   => "#7C3AED",
                FormTemplateType.MEDOIL => "#B45309",
                _                      => "#065F46"
            };

            return Document.Create(container =>
            {
                container.Page(page =>
                {
                    page.Size(PageSizes.A4);
                    page.Margin(1.5f, Unit.Centimetre);
                    page.DefaultTextStyle(x => x.FontSize(9).FontFamily("Arial"));

                    page.Header().Column(col =>
                    {
                        col.Item().Border(1.5f).BorderColor(accentColor).Row(row =>
                        {
                            row.ConstantItem(170).Background(accentColor)
                                .Padding(10).Column(c =>
                            {
                                c.Item().Text("POULINA GROUP HOLDING")
                                    .Bold().FontSize(10).FontColor("#FFFFFF");
                                c.Item().Text("BULLETIN DE RÉSULTATS D'ANALYSES")
                                    .FontSize(8).FontColor("#E5E7EB");
                                c.Item().PaddingTop(4)
                                    .Text(request.Laboratory?.Name ?? "")
                                    .Bold().FontSize(13).FontColor("#FCD34D");
                            });

                            row.RelativeItem().Padding(10).Column(c =>
                            {
                                c.Item().AlignCenter()
                                    .Text("BULLETIN DE RÉSULTATS D'ANALYSES")
                                    .Bold().FontSize(13).FontColor(accentColor);
                                c.Item().PaddingTop(2).AlignCenter()
                                    .Text($"Réf : PGH-{request.Id:D6}")
                                    .Bold().FontSize(11).FontColor("#374151");
                                c.Item().PaddingTop(2).AlignCenter()
                                    .Text($"Date de validation : {DateTime.UtcNow:dd/MM/yyyy}")
                                    .FontSize(9).FontColor("#6B7280");
                            });

                            row.ConstantItem(130).Padding(8).Column(c =>
                            {
                                c.Item().Border(1).BorderColor(accentColor)
                                    .Background("#F0FDF4").Padding(5).Column(inner =>
                                {
                                    inner.Item().Text("STATUT")
                                        .Bold().FontSize(7).FontColor(accentColor);
                                    inner.Item().PaddingTop(2)
                                        .Text("✓ VALIDÉ")
                                        .Bold().FontSize(11).FontColor("#10B981");
                                    inner.Item().PaddingTop(4).Text("N° DEMANDE")
                                        .Bold().FontSize(7).FontColor(accentColor);
                                    inner.Item().PaddingTop(2)
                                        .Text($"{request.Id:D6}")
                                        .Bold().FontSize(11).FontColor(accentColor);
                                });
                            });
                        });
                        col.Item().PaddingTop(4);
                    });

                    page.Content().Column(col =>
                    {
                        // SECTION I — IDENTIFICATION
                        col.Item().Border(1).BorderColor("#D1D5DB").Column(section =>
                        {
                            section.Item().Background(accentColor).Padding(4)
                                .Text("I. IDENTIFICATION")
                                .Bold().FontSize(9).FontColor("#FFFFFF");

                            section.Item().Padding(8).Element(container =>
                                RenderInfoTable(container, new List<(string, string)>
                                {
                                    ("NOM ET PRÉNOM :", $"{request.Client?.FirstName} {request.Client?.LastName}"),
                                    ("DATE SOUMISSION :", request.SubmittedAt.ToString("dd/MM/yyyy")),
                                    ("FILIALE :", request.Client?.FilialeName ?? ""),
                                    ("LABORATOIRE :", request.Laboratory?.Name ?? "")
                                }));
                        });

                        col.Item().PaddingTop(5);

                        // SECTION II — RÉSULTATS
                        col.Item().Border(1).BorderColor("#D1D5DB").Column(section =>
                        {
                            section.Item().Background(accentColor).Padding(4)
                                .Text("II. RÉSULTATS DES ANALYSES")
                                .Bold().FontSize(9).FontColor("#FFFFFF");

                            var sampleIndex = 1;
                            foreach (var sample in request.Samples)
                            {
                                section.Item().Padding(6).Column(sCol =>
                                {
                                    sCol.Item().Background("#F0FDF4").Padding(5)
                                        .Text($"Échantillon {sampleIndex} : {sample.Type} " +
                                              $"— {sample.Quantity} {sample.Unit}")
                                        .Bold().FontSize(9).FontColor(accentColor);

                                    sCol.Item().Table(table =>
                                    {
                                        table.ColumnsDefinition(c =>
                                        {
                                            c.RelativeColumn(3);
                                            c.RelativeColumn(1);
                                            c.RelativeColumn(1);
                                            c.RelativeColumn(1);
                                            c.RelativeColumn(1);
                                            c.RelativeColumn(1);
                                        });

                                        table.Header(h =>
                                        {
                                            foreach (var t in new[] {
                                                "TYPE D'ANALYSE", "VALEUR MESURÉE",
                                                "MIN REF", "MAX REF",
                                                "UNITÉ", "STATUT" })
                                            {
                                                h.Cell().Background(accentColor)
                                                    .Padding(5).Text(t).Bold()
                                                    .FontSize(8).FontColor("#FFFFFF");
                                            }
                                        });

                                        foreach (var result in sample.Results)
                                        {
                                            var isAnomaly = result.IsAnomaly;
                                            var bg = isAnomaly ? "#FEF2F2" : "#FFFFFF";

                                            table.Cell().Background(bg).BorderBottom(1)
                                                .BorderColor("#E5E7EB").Padding(4)
                                                .Text(result.AnalysisName ?? "")
                                                .FontSize(8);
                                            table.Cell().Background(bg).BorderBottom(1)
                                                .BorderColor("#E5E7EB").Padding(4)
                                                .AlignCenter()
                                                .Text(result.MeasuredValue.ToString("F2"))
                                                .Bold().FontSize(9)
                                                .FontColor(isAnomaly ? "#DC2626" : "#065F46");
                                            table.Cell().Background(bg).BorderBottom(1)
                                                .BorderColor("#E5E7EB").Padding(4)
                                                .AlignCenter()
                                                .Text(result.LowerBound.ToString("F2"))
                                                .FontSize(8);
                                            table.Cell().Background(bg).BorderBottom(1)
                                                .BorderColor("#E5E7EB").Padding(4)
                                                .AlignCenter()
                                                .Text(result.UpperBound.ToString("F2"))
                                                .FontSize(8);
                                            table.Cell().Background(bg).BorderBottom(1)
                                                .BorderColor("#E5E7EB").Padding(4)
                                                .AlignCenter()
                                                .Text(result.Unit ?? "")
                                                .FontSize(8);
                                            table.Cell().Background(bg).BorderBottom(1)
                                                .BorderColor("#E5E7EB").Padding(4)
                                                .AlignCenter()
                                                .Text(isAnomaly ? "⚠ ANOMALIE" : "✓ NORMAL")
                                                .Bold().FontSize(8)
                                                .FontColor(isAnomaly ? "#DC2626" : "#10B981");
                                        }
                                    });
                                    sampleIndex++;
                                });
                            }
                        });

                        col.Item().PaddingTop(5);

                        // LÉGENDE + VISA
                        col.Item().Border(1).BorderColor("#D1D5DB").Row(row =>
                        {
                            row.RelativeItem().BorderRight(1)
                                .BorderColor("#D1D5DB").Padding(8).Column(c =>
                            {
                                c.Item().Text("LÉGENDE")
                                    .Bold().FontSize(8).FontColor("#374151");
                                c.Item().PaddingTop(4).Row(r =>
                                {
                                    r.ConstantItem(14).Height(14).Border(1)
                                        .BorderColor("#DC2626").Background("#FEE2E2")
                                        .AlignCenter().AlignMiddle()
                                        .Text("⚠").FontSize(8).FontColor("#DC2626");
                                    r.RelativeItem().PaddingLeft(6)
                                        .Text("Valeur hors des bornes de référence")
                                        .FontSize(8).FontColor("#6B7280");
                                });
                                c.Item().PaddingTop(4).Row(r =>
                                {
                                    r.ConstantItem(14).Height(14).Border(1)
                                        .BorderColor("#10B981").Background("#ECFDF5")
                                        .AlignCenter().AlignMiddle()
                                        .Text("✓").FontSize(8).FontColor("#10B981");
                                    r.RelativeItem().PaddingLeft(6)
                                        .Text("Valeur dans les bornes de référence")
                                        .FontSize(8).FontColor("#6B7280");
                                });
                            });

                            row.RelativeItem().Padding(8).Column(c =>
                            {
                                c.Item().Text("VISA DU CHEF DE LABORATOIRE")
                                    .Bold().FontSize(8).FontColor("#374151");
                                c.Item().PaddingTop(4)
                                    .Text($"Laboratoire : {request.Laboratory?.Name}")
                                    .FontSize(8);
                                c.Item().PaddingTop(2)
                                    .Text($"Date : {DateTime.UtcNow:dd/MM/yyyy}")
                                    .FontSize(8);
                                c.Item().PaddingTop(8)
                                    .Text("Signature : _______________________")
                                    .FontSize(8).FontColor("#9CA3AF");
                                c.Item().PaddingTop(4).MinHeight(25)
                                    .Border(1).BorderColor("#E5E7EB")
                                    .Background("#F9FAFB");
                            });
                        });
                    });

                    page.Footer().PaddingTop(4).BorderTop(1)
                        .BorderColor("#E5E7EB").Row(row =>
                    {
                        row.RelativeItem()
                            .Text("Ce bulletin ne peut être reproduit que dans son intégralité")
                            .FontSize(7).FontColor("#9CA3AF");
                        row.AutoItem().Text(text =>
                        {
                            text.Span("Page ").FontSize(7).FontColor("#9CA3AF");
                            text.CurrentPageNumber().FontSize(7).FontColor("#9CA3AF");
                            text.Span(" / ").FontSize(7).FontColor("#9CA3AF");
                            text.TotalPages().FontSize(7).FontColor("#9CA3AF");
                        });
                        row.RelativeItem().AlignRight()
                            .Text($"Réf : {request.Laboratory?.Name}-{request.Id:D6}-{DateTime.UtcNow:yyyyMMdd}")
                            .FontSize(7).FontColor("#9CA3AF");
                    });
                });
            }).GeneratePdf();
        }

        // -------------------------------------------------------
        // Méthodes utilitaires
        // -------------------------------------------------------

        // Remplace Grid (obsolète) — affiche des paires label/valeur en tableau
        private static void RenderInfoTable(
            IContainer container,
            List<(string Label, string Value)> rows)
        {
            container.Table(table =>
            {
                table.ColumnsDefinition(c =>
                {
                    c.RelativeColumn(1); // Label
                    c.RelativeColumn(3); // Valeur
                });

                foreach (var (label, value) in rows)
                {
                    table.Cell().Background("#F3F4F6")
                        .BorderBottom(1).BorderColor("#E5E7EB")
                        .Padding(4)
                        .Text(label).Bold().FontSize(8).FontColor("#6B7280");

                    table.Cell().BorderBottom(1).BorderColor("#E5E7EB")
                        .Padding(4)
                        .Text(value).FontSize(8);
                }
            });
        }

        private static void AddCheckbox(ColumnDescriptor col, string label)
        {
            col.Item().PaddingBottom(3).Row(r =>
            {
                r.ConstantItem(12).Height(12).Border(1)
                    .BorderColor("#D1D5DB").Background("#FFFFFF");
                r.AutoItem().PaddingLeft(4)
                    .Text(label).FontSize(8).FontColor("#374151");
            });
        }
    }
}