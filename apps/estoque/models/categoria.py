from django.db import models
from django.utils.text import slugify
from apps.estoque.domain.tipos import FamiliaProduto


class CategoriaProduto(models.Model):
    """
    Categorias hierárquicas para o estoque moveleiro (Tarugo MVP)
    Exemplo: Matéria-Prima → MDF
             Ferragens → Dobradiças
    """
    nome = models.CharField(max_length=120, verbose_name="Nome da Categoria")
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="subcategorias",
        verbose_name="Categoria Pai"
    )
    descricao = models.TextField(blank=True, null=True, verbose_name="Descrição")
    ordem = models.PositiveIntegerField(default=0, verbose_name="Ordem")
    familia = models.CharField(
        max_length=30,
        choices=FamiliaProduto.choices(),
        default=FamiliaProduto.OUTROS,
        verbose_name="Família de Produto"
    )

    class Meta:
        verbose_name = "Categoria de Produto"
        verbose_name_plural = "Categorias de Produtos"
        ordering = ["ordem", "nome"]
        unique_together = [["nome", "parent"]]

    def __str__(self):
        if self.parent:
            return f"{self.parent.nome} → {self.nome}"
        return self.nome

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nome)
        super().save(*args, **kwargs)