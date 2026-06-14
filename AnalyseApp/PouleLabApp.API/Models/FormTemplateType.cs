namespace PouleLabApp.API.Models
{
    // Type de formulaire — un par marque/laboratoire
    // Chaque template a ses propres sections spécifiques au métier
    public enum FormTemplateType
    {
        DICK,    // Laboratoire vétérinaire / aviculture
        SNA,     // Analyses industrielles standard
        GIPA,    // Analyses huiles et lubrifiants
        MEDOIL   // Analyses corps gras et huiles alimentaires
    }
}