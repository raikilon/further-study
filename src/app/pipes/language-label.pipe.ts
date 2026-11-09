import { Pipe, PipeTransform } from '@angular/core';
import { LanguageCode } from '../program.model';
import { LANGUAGE_LABELS } from '../catalog/catalog-labels';

@Pipe({ name: 'languageLabel', standalone: true, pure: true })
export class LanguageLabelPipe implements PipeTransform {
  transform(language: string): string {
    return LANGUAGE_LABELS[language as LanguageCode] ?? language;
  }
}
