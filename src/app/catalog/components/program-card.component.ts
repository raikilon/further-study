import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';
import { Program } from '../../program.model';
import { CheckedDatePipe } from '../../pipes/checked-date.pipe';
import { FormatLabelPipe } from '../../pipes/format-label.pipe';
import { LanguageLabelPipe } from '../../pipes/language-label.pipe';
import { ProgramDatePipe } from '../../pipes/program-date.pipe';
import { ProgramFeePipe } from '../../pipes/program-fee.pipe';
import { SubjectLabelPipe } from '../../pipes/subject-label.pipe';

@Component({
  selector: 'app-program-card',
  standalone: true,
  imports: [CommonModule, CheckedDatePipe, FormatLabelPipe, LanguageLabelPipe, ProgramDatePipe, ProgramFeePipe, SubjectLabelPipe],
  template: `
    <article class="program-card">
      <div class="card-topline">
        <span class="credential-pill" [class.mas]="program.credential === 'MAS'">{{ program.credential }}</span>
        <span class="verified-label">Checked {{ program.verifiedAt | checkedDate }} <em *ngIf="program.catalogStatus === 'not-reconfirmed'">· not re-confirmed</em><em *ngIf="program.confidence === 'low'">· partial listing</em></span>
      </div>
      <h3>{{ program.title }}</h3>
      <p class="program-provider">{{ program.provider }}</p>
      <p class="program-summary">{{ program.summary }}</p>
      <p class="subject-label">{{ program.subject | subjectLabel }}</p>
      <div class="card-meta">
        <div class="meta-item"><span class="meta-label">NEXT START</span><span class="meta-value">{{ program.nextStart | programDate:program.nextStartLabel }}</span></div>
        <div class="meta-item"><span class="meta-label">LOCATION</span><span class="meta-value" [title]="program.city">{{ program.city || 'Not listed' }}</span></div>
        <div class="meta-item"><span class="meta-label">DURATION</span><span class="meta-value">{{ program.duration || 'Not listed' }}</span></div>
        <div class="meta-item"><span class="meta-label">FEE</span><span class="meta-value" [title]="program | programFee">{{ program | programFee }}</span></div>
        <div class="meta-item"><span class="meta-label">CREDITS</span><span class="meta-value">{{ program.ects === null ? 'Not listed' : (program.ects + ' ECTS') }}</span></div>
        <div class="meta-item"><span class="meta-label">FORMAT</span><span class="meta-value">{{ program.format | formatLabel }}</span></div>
      </div>
      <div class="card-bottom">
        <div class="language-chips" aria-label="Teaching language"><span class="language-chip" *ngFor="let code of program.languages">{{ code | languageLabel }}</span><span class="language-chip" *ngIf="!program.languages.length">Not listed</span></div>
        <a class="source-link" [href]="program.sourceUrl" target="_blank" rel="noreferrer">Official page <span aria-hidden="true">↗</span></a>
      </div>
    </article>
  `,
})
export class ProgramCardComponent {
  @Input({ required: true }) program!: Program;
}
