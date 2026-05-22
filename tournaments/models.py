from django.db import models
from resources.models import Resource, Sport


class Tournament(models.Model):
    FORMAT_CHOICES = [
        ('round_robin', 'Round Robin'),
        ('groups_elimination', 'Grupos + Eliminación'),
    ]
    GENDER_CHOICES = [
        ('M', 'Masculino'),
        ('F', 'Femenino'),
    ]
    CATEGORY_CHOICES = [
        ('libre', 'Libre'),
        ('veteranos', 'Veteranos'),
    ]
    STATUS_CHOICES = [
        ('draft', 'Borrador'),
        ('open', 'Inscripción abierta'),
        ('in_progress', 'En curso'),
        ('finished', 'Finalizado'),
    ]

    name = models.CharField(max_length=200, verbose_name='Nombre')
    sport = models.ForeignKey(Sport, on_delete=models.PROTECT, verbose_name='Deporte')
    format = models.CharField(max_length=30, choices=FORMAT_CHOICES, verbose_name='Formato')
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, verbose_name='Género')
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='libre',
        verbose_name='Categoría'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name='Estado'
    )
    min_players = models.PositiveIntegerField(default=5, verbose_name='Mínimo de jugadores')
    max_players = models.PositiveIntegerField(default=15, verbose_name='Máximo de jugadores')
    start_date = models.DateField(null=True, blank=True, verbose_name='Fecha de inicio')
    resource = models.ForeignKey(
        Resource,
        on_delete=models.PROTECT,
        verbose_name='Cancha',
        null=True,
        blank=True
    )
    notes = models.TextField(blank=True, verbose_name='Notas')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Torneo'
        verbose_name_plural = 'Torneos'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.get_gender_display()} — {self.get_category_display()})"

    @property
    def total_teams(self):
        return self.teams.count()


class Team(models.Model):
    tournament = models.ForeignKey(
        Tournament,
        on_delete=models.CASCADE,
        related_name='teams',
        verbose_name='Torneo'
    )
    name = models.CharField(max_length=200, verbose_name='Nombre del equipo')
    contact_name = models.CharField(max_length=200, verbose_name='Nombre del contacto')
    contact_phone = models.CharField(max_length=20, verbose_name='Teléfono del contacto')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Equipo'
        verbose_name_plural = 'Equipos'
        ordering = ['name']
        unique_together = ['tournament', 'name']

    def __str__(self):
        return f"{self.name} ({self.tournament.name})"

    @property
    def total_players(self):
        return self.players.filter(is_active=True).count()

    @property
    def is_complete(self):
        return self.total_players >= self.tournament.min_players


class Player(models.Model):
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name='players',
        verbose_name='Equipo'
    )
    name = models.CharField(max_length=200, verbose_name='Nombre completo')
    dni = models.CharField(max_length=20, verbose_name='DNI')
    is_active = models.BooleanField(default=True, verbose_name='Habilitado')
    injury_replacement = models.BooleanField(
        default=False,
        verbose_name='Reemplazo por lesión'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Jugador'
        verbose_name_plural = 'Jugadores'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} — DNI {self.dni}"

    def clean(self):
        from django.core.exceptions import ValidationError

        # Validar que el jugador no esté en otro equipo del mismo torneo
        if self.pk is None:
            tournament = self.team.tournament
            existing = Player.objects.filter(
                dni=self.dni,
                team__tournament=tournament,
            ).exclude(team=self.team)
            if existing.exists():
                raise ValidationError(
                    f'El jugador con DNI {self.dni} ya está registrado en otro equipo de este torneo.'
                )

            # Validar que no se agreguen jugadores si el torneo ya inició
            if tournament.status == 'in_progress' and not self.injury_replacement:
                raise ValidationError(
                    'No se pueden agregar jugadores a un torneo en curso salvo por lesión grave.'
                )

            # Validar máximo de jugadores
            if self.team.total_players >= tournament.max_players:
                raise ValidationError(
                    f'El equipo ya tiene el máximo de {tournament.max_players} jugadores.'
                )


class Group(models.Model):
    tournament = models.ForeignKey(
        Tournament,
        on_delete=models.CASCADE,
        related_name='groups',
        verbose_name='Torneo'
    )
    name = models.CharField(max_length=50, verbose_name='Nombre')
    teams = models.ManyToManyField(Team, related_name='groups', verbose_name='Equipos')

    class Meta:
        verbose_name = 'Grupo'
        verbose_name_plural = 'Grupos'
        ordering = ['name']

    def __str__(self):
        return f"Grupo {self.name} — {self.tournament.name}"


class Match(models.Model):
    STATUS_CHOICES = [
        ('scheduled', 'Programado'),
        ('in_progress', 'En curso'),
        ('finished', 'Finalizado'),
        ('cancelled', 'Cancelado'),
    ]
    STAGE_CHOICES = [
        ('group', 'Fase de grupos'),
        ('round_of_16', 'Octavos'),
        ('quarterfinal', 'Cuartos de final'),
        ('semifinal', 'Semifinal'),
        ('third_place', 'Tercer puesto'),
        ('final', 'Final'),
    ]

    tournament = models.ForeignKey(
        Tournament,
        on_delete=models.CASCADE,
        related_name='matches',
        verbose_name='Torneo'
    )
    group = models.ForeignKey(
        Group,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='matches',
        verbose_name='Grupo'
    )
    stage = models.CharField(
        max_length=20,
        choices=STAGE_CHOICES,
        default='group',
        verbose_name='Fase'
    )
    home_team = models.ForeignKey(
        Team,
        on_delete=models.PROTECT,
        related_name='home_matches',
        verbose_name='Equipo local'
    )
    away_team = models.ForeignKey(
        Team,
        on_delete=models.PROTECT,
        related_name='away_matches',
        verbose_name='Equipo visitante'
    )
    resource = models.ForeignKey(
        Resource,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name='Cancha'
    )
    date = models.DateField(null=True, blank=True, verbose_name='Fecha')
    start_time = models.TimeField(null=True, blank=True, verbose_name='Hora')
    home_score = models.PositiveIntegerField(null=True, blank=True, verbose_name='Goles local')
    away_score = models.PositiveIntegerField(null=True, blank=True, verbose_name='Goles visitante')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='scheduled',
        verbose_name='Estado'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Partido'
        verbose_name_plural = 'Partidos'
        ordering = ['date', 'start_time']

    def __str__(self):
        return f"{self.home_team.name} vs {self.away_team.name} — {self.date}"

    @property
    def result(self):
        if self.home_score is None or self.away_score is None:
            return None
        if self.home_score > self.away_score:
            return 'home'
        elif self.away_score > self.home_score:
            return 'away'
        return 'draw'


class Standing(models.Model):
    tournament = models.ForeignKey(
        Tournament,
        on_delete=models.CASCADE,
        related_name='standings',
        verbose_name='Torneo'
    )
    group = models.ForeignKey(
        Group,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='standings',
        verbose_name='Grupo'
    )
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name='standings',
        verbose_name='Equipo'
    )
    played = models.PositiveIntegerField(default=0, verbose_name='PJ')
    won = models.PositiveIntegerField(default=0, verbose_name='PG')
    drawn = models.PositiveIntegerField(default=0, verbose_name='PE')
    lost = models.PositiveIntegerField(default=0, verbose_name='PP')
    goals_for = models.PositiveIntegerField(default=0, verbose_name='GF')
    goals_against = models.PositiveIntegerField(default=0, verbose_name='GC')

    class Meta:
        verbose_name = 'Posición'
        verbose_name_plural = 'Posiciones'
        ordering = ['-won', '-goals_for']
        unique_together = ['tournament', 'group', 'team']

    def __str__(self):
        return f"{self.team.name} — {self.tournament.name}"

    @property
    def points(self):
        return (self.won * 3) + self.drawn

    @property
    def goal_difference(self):
        return self.goals_for - self.goals_against